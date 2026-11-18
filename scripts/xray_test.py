"""Real-world proxy testing through a local Xray instance.

One Xray process hosts a batch of SOCKS inbounds (one per node), every
inbound is routed to its own outbound. That lets us run hundreds of
independent end-to-end HTTP probes in parallel with a single binary.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional, Sequence

try:  # optional at import time so --dry-run works without the deps
    import aiohttp
    from aiohttp_socks import ProxyConnector
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore
    ProxyConnector = None  # type: ignore

from config import (
    PROBE_CONCURRENCY,
    PROBE_TIMEOUT,
    PROBE_URLS,
    SPEED_CONCURRENCY,
    SPEED_TIMEOUT,
    SPEED_URL,
    TRACE_TIMEOUT,
    TRACE_URL,
    USER_AGENT,
    XRAY_BASE_PORT,
    XRAY_BATCH_SIZE,
    XRAY_READY_TIMEOUT,
)
from parse import Node
from xrayconfig import build_config

log = logging.getLogger("xray")

Handler = Callable[[Sequence[Node], Sequence[int]], Awaitable[list]]


# --- binary / ports --------------------------------------------------------


def find_xray() -> str:
    candidates = [
        os.getenv("XRAY_BIN", ""),
        str(Path(__file__).resolve().parent.parent / "bin" / "xray"),
        shutil.which("xray") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "xray binary not found: run scripts/setup.sh or set XRAY_BIN"
    )


def _pick_ports(count: int, start: int = XRAY_BASE_PORT) -> list[int]:
    ports: list[int] = []
    port = start
    while len(ports) < count:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            ports.append(port)
        except OSError:
            pass
        finally:
            sock.close()
        port += 1
        if port > 65000:
            raise RuntimeError("no free ports available")
    return ports


# --- process control -------------------------------------------------------


async def _start(config: dict) -> tuple[subprocess.Popen, Path]:
    binary = find_xray()
    fd, path = tempfile.mkstemp(prefix="xray-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(config, fh)
    proc = subprocess.Popen(
        [binary, "run", "-c", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc, Path(path)


async def _stop(proc: subprocess.Popen, cfg: Path) -> None:
    try:
        proc.terminate()
        try:
            await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await asyncio.to_thread(proc.wait)
    except Exception:
        pass
    try:
        cfg.unlink(missing_ok=True)
    except Exception:
        pass


async def _wait_ready(proc: subprocess.Popen, ports: Sequence[int], timeout: float) -> bool:
    pending = set(ports)
    deadline = time.monotonic() + timeout
    while pending and time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        for port in list(pending):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port), timeout=0.3
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                pending.discard(port)
            except Exception:
                pass
        if pending:
            await asyncio.sleep(0.15)
    return not pending


# --- HTTP over SOCKS -------------------------------------------------------


async def _http_get(port: int, url: str, timeout: float) -> Optional[tuple[float, bytes]]:
    if aiohttp is None or ProxyConnector is None:
        raise RuntimeError("aiohttp and aiohttp-socks are required: pip install -r requirements.txt")
    connector = ProxyConnector.from_url(f"socks5://127.0.0.1:{port}", rdns=True)
    start = time.perf_counter()
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
            async with session.get(
                url, ssl=False, allow_redirects=False, headers={"User-Agent": USER_AGENT}
            ) as resp:
                body = await resp.read()
                elapsed = (time.perf_counter() - start) * 1000
                if resp.status in (200, 204):
                    return elapsed, body
    except Exception:
        return None
    finally:
        try:
            await connector.close()
        except Exception:
            pass
    return None


async def _probe_one(node: Node, port: int, sem: asyncio.Semaphore) -> bool:
    async with sem:
        for url in PROBE_URLS:
            result = await _http_get(port, url, PROBE_TIMEOUT)
            if result is not None:
                elapsed = result[0]
                node.ok += 1
                node.latency_ms = elapsed if not node.latency_ms else min(node.latency_ms, elapsed)
                return True
            node.fail += 1
    return False


async def _probe_chunk(nodes: Sequence[Node], ports: Sequence[int]) -> list[bool]:
    sem = asyncio.Semaphore(PROBE_CONCURRENCY)
    return list(
        await asyncio.gather(*(_probe_one(n, p, sem) for n, p in zip(nodes, ports)))
    )


async def _speed_chunk(nodes: Sequence[Node], ports: Sequence[int]) -> list[Optional[float]]:
    sem = asyncio.Semaphore(SPEED_CONCURRENCY)

    async def one(node: Node, port: int) -> Optional[float]:
        async with sem:
            result = await _http_get(port, SPEED_URL, SPEED_TIMEOUT)
            if result is None:
                return None
            elapsed_ms, body = result
            if not body or elapsed_ms <= 0:
                return None
            return (len(body) * 8) / elapsed_ms  # kbit/s

    return list(await asyncio.gather(*(one(n, p) for n, p in zip(nodes, ports))))


async def _country_chunk(nodes: Sequence[Node], ports: Sequence[int]) -> list[str]:
    sem = asyncio.Semaphore(PROBE_CONCURRENCY)

    async def one(node: Node, port: int) -> str:
        async with sem:
            result = await _http_get(port, TRACE_URL, TRACE_TIMEOUT)
            if result is None:
                return ""
            match = re.search(rb"^loc=([A-Z]{2})$", result[1], re.MULTILINE)
            return match.group(1).decode() if match else ""

    return list(await asyncio.gather(*(one(n, p) for n, p in zip(nodes, ports))))


# --- orchestration ---------------------------------------------------------


async def _run_chunk(nodes: list[Node], handler: Handler) -> list:
    ports = _pick_ports(len(nodes))
    cfg_obj = build_config(nodes, ports)
    proc, cfg_path = await _start(cfg_obj)
    ready = await _wait_ready(proc, ports, XRAY_READY_TIMEOUT)
    if not ready:
        await _stop(proc, cfg_path)
        log.warning("xray failed to start for %d node(s), splitting", len(nodes))
        if len(nodes) == 1:
            return [None]
        mid = len(nodes) // 2
        left = await _run_chunk(nodes[:mid], handler)
        right = await _run_chunk(nodes[mid:], handler)
        return left + right
    try:
        return await handler(nodes, ports)
    finally:
        await _stop(proc, cfg_path)


async def run_stage(
    nodes: list[Node],
    handler: Handler,
    batch_size: int = XRAY_BATCH_SIZE,
    deadline: Optional[float] = None,
) -> list:
    results: list = []
    total = len(nodes)
    for offset in range(0, total, batch_size):
        if deadline and time.monotonic() > deadline:
            log.warning("time budget exhausted, %d node(s) skipped", total - offset)
            results.extend([None] * (total - offset))
            break
        chunk = nodes[offset : offset + batch_size]
        started = time.perf_counter()
        chunk_results = await _run_chunk(chunk, handler)
        results.extend(chunk_results)
        log.info(
            "tested %d/%d (%.1fs)",
            min(offset + batch_size, total),
            total,
            time.perf_counter() - started,
        )
    return results


async def probe_nodes(nodes: list[Node], deadline: Optional[float] = None) -> list[Node]:
    results = await run_stage(nodes, _probe_chunk, deadline=deadline)
    alive = [node for node, ok in zip(nodes, results) if ok]
    log.info("http probe: %d alive / %d tested", len(alive), len(nodes))
    return alive


async def resolve_countries(nodes: list[Node], deadline: Optional[float] = None) -> None:
    results = await run_stage(nodes, _country_chunk, deadline=deadline)
    for node, cc in zip(nodes, results):
        if cc:
            node.country = cc


async def measure_speeds(nodes: list[Node], deadline: Optional[float] = None) -> None:
    results = await run_stage(nodes, _speed_chunk, deadline=deadline)
    for node, speed in zip(nodes, results):
        if speed:
            node.speed_kbps = round(speed, 1)
