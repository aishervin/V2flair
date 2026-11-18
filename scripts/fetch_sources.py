"""Fetch subscription sources from sources.txt."""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

from config import FETCH_MAX_BYTES, FETCH_TIMEOUT, USER_AGENT

log = logging.getLogger("fetch")


def load_sources(path: str | Path) -> list[str]:
    path = Path(path)
    urls: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url = line.split()[0]
        if "#" in url and not url.startswith("http"):
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _fetch(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"HTTP {resp.status}")
        raw = resp.read(FETCH_MAX_BYTES)
        charset = resp.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, "ignore")
    except LookupError:
        return raw.decode("utf-8", "ignore")


def fetch_all(urls: list[str], workers: int = 16) -> list[tuple[str, str]]:
    """Return [(source, body)] for every reachable source, in sources.txt order."""
    bodies: dict[str, str] = {}
    workers = max(1, min(workers, len(urls) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch, url): url for url in urls}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                body = fut.result()
            except Exception as exc:  # noqa: BLE001 - network errors are expected
                log.warning("source failed: %s (%s)", _short(url), exc.__class__.__name__)
                continue
            if not body or len(body) < 16:
                log.warning("source empty: %s", _short(url))
                continue
            log.info("source ok: %-60s %8d bytes", _short(url), len(body))
            bodies[url] = body
    # Order matters: the first sources are the priority ones.
    return [(url, bodies[url]) for url in urls if url in bodies]


def _short(url: str) -> str:
    return url.replace("https://", "").replace("http://", "")[:70]
