"""Fast parallel TCP pre-filter (pure stdlib)."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable

from config import TCP_CONCURRENCY, TCP_TIMEOUT
from parse import Node

log = logging.getLogger("tcp")


async def _probe(node: Node, timeout: float, sem: asyncio.Semaphore) -> bool:
    async with sem:
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(node.host, node.port), timeout=timeout
            )
            node.tcp_ms = round((time.perf_counter() - start) * 1000, 1)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            return False


async def tcp_filter(
    nodes: Iterable[Node],
    concurrency: int = TCP_CONCURRENCY,
    timeout: float = TCP_TIMEOUT,
) -> list[Node]:
    nodes = list(nodes)
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*(_probe(n, timeout, sem) for n in nodes))
    alive = [n for n, ok in zip(nodes, results) if ok]
    alive.sort(key=lambda n: n.tcp_ms)
    log.info(
        "tcp filter: %d alive / %d tested (%.1f%%)",
        len(alive),
        len(nodes),
        (len(alive) / len(nodes) * 100) if nodes else 0,
    )
    return alive
