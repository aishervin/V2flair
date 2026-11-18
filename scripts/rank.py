"""Quality scoring and final selection."""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Iterable

from config import (
    BRAND,
    HARD_MAX_NODES,
    MAX_LATENCY_MS,
    MIN_SPEED_FLOOR_KBPS,
    MIN_SPEED_KBPS,
    MIN_STABILITY,
)
from geoip import GeoIP
from parse import Node, extract_flag_from_text, flag_for

log = logging.getLogger("rank")


def latency_score(ms: float) -> float:
    if ms <= 0:
        return 0.0
    return max(0.0, min(1.0, (2600.0 - ms) / 2500.0))


def speed_score(kbps: float) -> float:
    if kbps <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log1p(kbps / 150.0) / math.log1p(8000.0 / 150.0)))


def stability(node: Node) -> float:
    total = node.ok + node.fail
    return (node.ok / total) if total else 0.0


def score_node(node: Node) -> float:
    score = (
        40.0 * latency_score(node.latency_ms)
        + 45.0 * speed_score(node.speed_kbps)
        + 15.0 * stability(node)
    )
    if node.security == "reality":
        score += 3.0
    if node.port in (443, 8443):
        score += 1.5
    if node.net in {"xhttp", "splithttp"}:
        score += 0.5
    node.score = round(score, 2)
    return node.score


def _passes(node: Node, min_speed: float, max_latency: float, skip_speed: bool) -> bool:
    if stability(node) < MIN_STABILITY:
        return False
    if node.latency_ms <= 0 or node.latency_ms > max_latency:
        return False
    if not skip_speed and node.speed_kbps < min_speed:
        return False
    return True


def select(
    nodes: Iterable[Node],
    limit: int,
    min_speed: float = MIN_SPEED_KBPS,
    max_latency: float = MAX_LATENCY_MS,
    skip_speed: bool = False,
) -> list[Node]:
    nodes = list(nodes)
    for node in nodes:
        score_node(node)

    candidates = [n for n in nodes if _passes(n, min_speed, max_latency, skip_speed)]
    speed = min_speed
    latency = max_latency
    while len(candidates) < limit and speed > MIN_SPEED_FLOOR_KBPS:
        speed = max(MIN_SPEED_FLOOR_KBPS, speed * 0.6)
        candidates = [n for n in nodes if _passes(n, speed, latency, skip_speed)]
        log.info("relaxed speed threshold to %.0f kbit/s -> %d candidates", speed, len(candidates))

    if len(candidates) < limit:
        latency = max_latency * 1.6
        candidates = [n for n in nodes if _passes(n, speed, latency, skip_speed)]
        log.info("relaxed latency to %.0f ms -> %d candidates", latency, len(candidates))

    if not candidates:
        candidates = [n for n in nodes if stability(n) >= MIN_STABILITY]
        log.warning("no node passed thresholds, falling back to %d alive node(s)", len(candidates))

    candidates.sort(key=lambda n: (-n.score, n.latency_ms, -n.speed_kbps))
    candidates = _dedupe_identity(candidates)
    return candidates[: min(limit, HARD_MAX_NODES)]


def _dedupe_identity(nodes: list[Node]) -> list[Node]:
    best: dict[str, Node] = {}
    for node in nodes:
        current = best.get(node.identity)
        if current is None or node.score > current.score:
            best[node.identity] = node
    return sorted(best.values(), key=lambda n: (-n.score, n.latency_ms))


def apply_flags(nodes: Iterable[Node], geo: GeoIP | None = None) -> None:
    """flag priority: real exit country > source remark > offline GeoIP > globe."""
    for node in nodes:
        if node.country:
            node.flag = flag_for(node.country)
        elif node.flag:
            pass
        elif geo is not None:
            cc = geo.country(node.host)
            node.country = cc
            node.flag = flag_for(cc)
        else:
            node.flag = extract_flag_from_text(node.raw_remark) or flag_for("")
        if not node.flag:
            node.flag = flag_for("")
        node.remark = f"{node.flag}{BRAND}"
