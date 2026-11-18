"""Real-world testing for hysteria2 nodes via the official hysteria client.

Hysteria2 is QUIC based; Xray cannot speak it. Each node gets its own local
client process with a SOCKS5 inbound, then the exact same HTTP probe / speed /
country logic as the VLESS stage runs through it.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional, Sequence

from config import (
    HY2_BATCH_SIZE,
    HY2_READY_TIMEOUT,
    XRAY_BASE_PORT,
)
from parse import Node
from xray_test import (
    _country_chunk,
    _pick_ports,
    _probe_chunk,
    _speed_chunk,
    _wait_ready,
)

log = logging.getLogger("hy2")

Handler = Callable[[Sequence[Node], Sequence[int]], Awaitable[list]]

HY2_PORT = XRAY_BASE_PORT + 5000


def find_hysteria() -> str:
    candidates = [
        os.getenv("HYSTERIA_BIN", ""),
        str(Path(__file__).resolve().parent.parent / "bin" / "hysteria"),
        shutil.which("hysteria") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "hysteria binary not found: run scripts/setup.sh or set HYSTERIA_BIN"
    )


def _config(node: Node, port: int) -> dict:
    tls: dict = {"sni": node.sni or node.host}
    if node.allow_insecure:
        tls["insecure"] = True
    if node.pin:
        tls["pinSHA256"] = node.pin
    if node.alpn:
        tls["alpn"] = [p for p in node.alpn.split(",") if p]
    cfg: dict = {
        "server": f"{'[' + node.host + ']' if ':' in node.host else node.host}:{node.port}",
        "auth": node.auth,
        "tls": tls,
        "socks5": {"listen": f"127.0.0.1:{port}"},
        "fastOpen": True,
        "lazy": True,
    }
    if node.obfs == "salamander" and node.obfs_password:
        cfg["obfs"] = {
            "type": "salamander",
            "salamander": {"password": node.obfs_password},
        }
    return cfg


async def _start(node: Node, port: int) -> tuple[subprocess.Popen, Path]:
    binary = find_hysteria()
    fd, path = tempfile.mkstemp(prefix="hy2-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(_config(node, port), fh)
    proc = subprocess.Popen(
        [binary, "client", "-c", path],
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


async def _run_chunk(nodes: list[Node], handler: Handler) -> list:
    ports = _pick_ports(len(nodes), start=HY2_PORT)
    try:
        find_hysteria()
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return [None] * len(nodes)

    procs: list[tuple[subprocess.Popen, Path]] = []
    try:
        for node, port in zip(nodes, ports):
            proc, path = await _start(node, port)
            procs.append((proc, path))
        ready = await asyncio.gather(
            *(_wait_ready(proc, [port], HY2_READY_TIMEOUT) for (proc, _), port in zip(procs, ports))
        )
        if not any(ready):
            log.warning("hysteria client never came up (%d node(s))", len(nodes))
            return [None] * len(nodes)
        return await handler(nodes, ports)
    finally:
        await asyncio.gather(*(_stop(p, c) for p, c in procs))


async def _run_stage(
    nodes: list[Node],
    handler: Handler,
    batch_size: int = HY2_BATCH_SIZE,
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
        results.extend(await _run_chunk(chunk, handler))
        log.info(
            "hy2 tested %d/%d (%.1fs)",
            min(offset + batch_size, total),
            total,
            time.perf_counter() - started,
        )
    return results


async def probe_nodes(nodes: list[Node], deadline: Optional[float] = None) -> list[Node]:
    results = await _run_stage(nodes, _probe_chunk, deadline=deadline)
    alive = [node for node, ok in zip(nodes, results) if ok]
    log.info("hy2 probe: %d alive / %d tested", len(alive), len(nodes))
    return alive


async def resolve_countries(nodes: list[Node], deadline: Optional[float] = None) -> None:
    results = await _run_stage(nodes, _country_chunk, deadline=deadline)
    for node, cc in zip(nodes, results):
        if cc:
            node.country = cc


async def measure_speeds(nodes: list[Node], deadline: Optional[float] = None) -> None:
    results = await _run_stage(nodes, _speed_chunk, deadline=deadline)
    for node, speed in zip(nodes, results):
        if speed:
            node.speed_kbps = round(speed, 1)


HANDLERS: dict[str, tuple[Callable, Callable, Callable]] = {
    "hysteria2": (probe_nodes, measure_speeds, resolve_countries),
}
