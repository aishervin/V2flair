#!/usr/bin/env python3
"""Local sanity check: build a real Xray config from live sources and probe it.

Usage:
    python3 scripts/selftest.py [--source URL] [--count 12]

This uses plain `curl` (no aiohttp needed) so it can be run on a phone/Termux
or any machine with the `xray` binary in ./bin.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_sources import _fetch  # noqa: E402
from parse import dedupe, parse_many  # noqa: E402
from tcptest import tcp_filter  # noqa: E402
from xray_test import _pick_ports, _wait_ready, find_xray  # noqa: E402
from xrayconfig import build_config  # noqa: E402

DEFAULT_SOURCE = "https://nodebuf.com/s/5J3iJ4Vog4Nm4GocwIJ_GCuG"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args()

    print(f"[*] fetching {args.source}")
    body = _fetch(args.source)
    nodes, stats = parse_many([(args.source, body)])
    nodes = dedupe(nodes)
    print(f"[*] parsed {len(nodes)} unique VLESS config(s)")

    nodes = nodes[: max(args.count * 6, 40)]
    alive = await tcp_filter(nodes)
    alive.sort(key=lambda n: n.tcp_ms)
    alive = alive[: args.count]
    if not alive:
        print("[!] no node passed TCP")
        return 1
    print(f"[*] testing {len(alive)} node(s) through xray...")

    ports = _pick_ports(len(alive))
    config = build_config(alive, ports)
    fd, path = tempfile.mkstemp(prefix="xray-selftest-", suffix=".json")
    with open(fd, "w", encoding="utf-8") as fh:
        json.dump(config, fh)

    proc = subprocess.Popen(
        [find_xray(), "run", "-c", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        if not await _wait_ready(proc, ports, 12):
            err = proc.stderr.read().decode("utf-8", "ignore")[:2000] if proc.stderr else ""
            print("[!] xray failed to start")
            print(err)
            return 2

        ok = 0
        for node, port in zip(alive, ports):
            start = time.perf_counter()
            result = subprocess.run(
                [
                    "curl", "-s", "-o", "/dev/null", "-m", "6",
                    "-x", f"socks5h://127.0.0.1:{port}",
                    "-w", "%{http_code}",
                    "http://cp.cloudflare.com/generate_204",
                ],
                capture_output=True,
                text=True,
            )
            elapsed = (time.perf_counter() - start) * 1000
            code = result.stdout.strip() or "err"
            good = code in {"204", "200"}
            ok += good
            print(
                f"  {'OK ' if good else 'FAIL'} {node.host}:{node.port} "
                f"{node.net}/{node.security} -> {code} ({elapsed:.0f} ms)"
            )

        print(f"[*] {ok}/{len(alive)} node(s) passed end-to-end HTTP")
        return 0 if ok else 3
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
