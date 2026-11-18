"""Write the publishable subscription files."""
from __future__ import annotations

import base64
import json
import logging
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from config import BRAND, MIN_SPEED_KBPS
from parse import Node, publish_uri

log = logging.getLogger("output")


def build_plain(nodes: Iterable[Node]) -> str:
    lines = [publish_uri(node) for node in nodes]
    return "\n".join(lines) + ("\n" if lines else "")


def write_outputs(
    nodes: list[Node],
    out_dir: str | Path,
    *,
    site_dir: str | Path | None = None,
    extra_stats: dict | None = None,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    plain = build_plain(nodes)
    encoded = base64.b64encode(plain.encode("utf-8")).decode("ascii")

    (out / "sub.txt").write_text(plain, encoding="utf-8", newline="\n")
    (out / "sub").write_text(encoded + "\n", encoding="ascii", newline="\n")
    (out / "base64.txt").write_text(encoded + "\n", encoding="ascii", newline="\n")

    countries = Counter(node.flag for node in nodes)
    stats = {
        "brand": BRAND,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nodes": len(nodes),
        "countries": len([c for c in countries if c != "\U0001F310"]),
        "best_latency_ms": min((n.latency_ms for n in nodes), default=0),
        "best_speed_mbps": round(max((n.speed_kbps for n in nodes), default=0) / 1000, 2),
        "min_speed_kbps": MIN_SPEED_KBPS,
        "flags": dict(countries),
    }
    if extra_stats:
        stats.update(extra_stats)
    (out / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if site_dir:
        site = Path(site_dir)
        if site.is_dir():
            for item in site.iterdir():
                target = out / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)

    log.info("wrote %d node(s) to %s", len(nodes), out)
    return stats
