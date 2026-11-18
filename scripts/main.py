#!/usr/bin/env python3
"""V2flair build pipeline.

collect -> parse -> dedupe -> TCP pre-filter -> real proxy test ->
speed test -> country lookup -> rank -> publish + verify
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from fetch_sources import fetch_all, load_sources
from geoip import GeoIP
from output import write_outputs
from parse import Node, dedupe, parse_many
from rank import apply_flags, select
from tcptest import tcp_filter
from verify import verify
import hy2_test
from xray_test import measure_speeds, probe_nodes, resolve_countries

log = logging.getLogger("main")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)-10s %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V2flair subscription builder")
    parser.add_argument("--sources", default=str(ROOT / "sources.txt"))
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument("--limit", type=int, default=config.DEFAULT_MAX_NODES)
    parser.add_argument("--max-test", type=int, default=3000, help="max nodes sent to xray")
    parser.add_argument("--max-latency", type=float, default=config.MAX_LATENCY_MS)
    parser.add_argument("--min-speed", type=float, default=config.MIN_SPEED_KBPS)
    parser.add_argument("--skip-speed", action="store_true")
    parser.add_argument("--skip-geo", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="collect + parse only")
    parser.add_argument("--verbose", action="store_true")
    return parser


async def run(args: argparse.Namespace) -> int:
    started = time.monotonic()
    deadline = started + config.TIME_BUDGET_SECONDS

    urls = load_sources(args.sources)
    log.info("sources: %d", len(urls))
    if not urls:
        log.error("no sources configured")
        return 2

    bodies = fetch_all(urls)
    if not bodies:
        log.error("every source failed")
        return 2

    nodes, stats = parse_many(bodies)
    log.info(
        "parsed: %d uri(s), %d valid, %d rejected from %d source(s)",
        stats["uris"], stats["accepted"], stats["rejected"], len(bodies),
    )

    nodes = dedupe(nodes)
    log.info("unique configs after dedupe: %d", len(nodes))
    if args.dry_run:
        by_source: dict[str, int] = {}
        for node in nodes:
            by_source[node.source] = by_source.get(node.source, 0) + 1
        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
            log.info("  %4d  %s", count, source)
        return 0
    if not nodes:
        log.error("no valid vless/hysteria2 configs found")
        return 2

    # hysteria2 is QUIC/UDP: the TCP pre-filter would throw it away, so it
    # goes straight to the real (hysteria) probe.
    vless = [n for n in nodes if n.kind == "vless"]
    hy2 = [n for n in nodes if n.kind != "vless"]
    log.info("candidates: %d vless / %d hysteria2", len(vless), len(hy2))

    vless = await tcp_filter(vless) if vless else []
    if not vless and not hy2:
        log.error("no node passed the TCP filter")
        return 2
    log.info("tcp alive: %d vless", len(vless))

    # Priority sources get a reserved slice of the budget instead of competing
    # with huge generic collectors; hysteria2 is rare and cheap to cover.
    hy2 = hy2[: config.HY2_MAX_TEST]

    quota = int(args.max_test * config.PRIORITY_TEST_SHARE)
    priority = sorted(
        (n for n in vless if n.source_rank < config.PRIORITY_SOURCES),
        key=lambda n: n.tcp_ms,
    )[:quota]
    rest = sorted(
        (n for n in vless if n.source_rank >= config.PRIORITY_SOURCES),
        key=lambda n: n.tcp_ms,
    )
    budget = max(0, args.max_test - len(hy2) - len(priority))
    rest = rest[:budget]
    log.info(
        "real-test budget: %d priority + %d general + %d hy2",
        len(priority), len(rest), len(hy2),
    )

    probed = await hy2_test.probe_nodes(hy2, deadline=deadline) if hy2 else []
    vless_probed = await probe_nodes(priority + rest, deadline=deadline)
    probed.extend(vless_probed)
    if not probed:
        log.error("no node passed the real proxy test")
        return 2

    vless_probed = [n for n in probed if n.kind == "vless"]
    hy2_probed = [n for n in probed if n.kind != "vless"]

    if not args.skip_geo:
        await resolve_countries(vless_probed, deadline=deadline)
        if hy2_probed:
            await hy2_test.resolve_countries(hy2_probed, deadline=deadline)

    if not args.skip_speed:
        await measure_speeds(
            sorted(vless_probed, key=lambda n: n.latency_ms)[: args.limit * 2],
            deadline=deadline,
        )
        if hy2_probed:
            await hy2_test.measure_speeds(
                sorted(hy2_probed, key=lambda n: n.latency_ms)[: args.limit],
                deadline=deadline,
            )

    final = select(
        probed,
        limit=args.limit,
        min_speed=args.min_speed,
        max_latency=args.max_latency,
        skip_speed=args.skip_speed,
    )

    geo = None if args.skip_geo else GeoIP()
    apply_flags(final, geo)
    if geo is not None:
        geo.close()

    elapsed = time.monotonic() - started
    stats_out = write_outputs(
        final,
        args.out,
        extra_stats={
            "sources": len(bodies),
            "collected": stats["accepted"],
            "unique": len(nodes),
            "tcp_alive": len(alive),
            "probed_alive": len(probed),
            "build_seconds": round(elapsed, 1),
        },
    )
    log.info(
        "done: %d published | best %.0f ms | %.1f Mbit/s",
        stats_out["nodes"],
        stats_out["best_latency_ms"],
        stats_out["best_speed_mbps"],
    )

    if not args.skip_verify:
        errors = verify(args.out)
        if errors:
            log.error("verification failed with %d error(s)", len(errors))
            return 3
        log.info("verification passed")

    return 0


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(args.verbose)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
