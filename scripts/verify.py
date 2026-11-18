"""Hard fail the build if the produced subscription is broken or dirty."""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from config import BRAND, MIN_PUBLISH_NODES
from parse import parse_uri

REMARK_RE = re.compile(r"^(?:[\U0001F1E6-\U0001F1FF]{2}|\U0001F310)" + re.escape(BRAND) + r"$")


def verify(out_dir: str | Path, min_nodes: int = MIN_PUBLISH_NODES) -> list[str]:
    out = Path(out_dir)
    errors: list[str] = []

    plain_path = out / "sub.txt"
    if not plain_path.is_file():
        return ["sub.txt is missing"]
    raw = plain_path.read_text(encoding="utf-8")
    if not raw.endswith("\n"):
        errors.append("sub.txt must end with a newline")
    lines = raw.splitlines()

    if len(lines) < min_nodes:
        errors.append(f"only {len(lines)} node(s) produced (minimum {min_nodes})")
    if any(not line.strip() for line in lines):
        errors.append("sub.txt contains empty lines")

    seen_lines: set[str] = set()
    seen_ids: set[str] = set()
    for index, line in enumerate(lines, 1):
        if line in seen_lines:
            errors.append(f"line {index}: duplicate line")
        seen_lines.add(line)

        node = parse_uri(line)
        if node is None:
            errors.append(f"line {index}: not a valid VLESS uri")
            continue

        try:
            parts = urlsplit(line)
            remark = unquote(parts.fragment or "")
        except ValueError:
            errors.append(f"line {index}: bad uri")
            continue
        if not REMARK_RE.match(remark):
            errors.append(f"line {index}: bad remark {remark!r}")
        if "#" not in line:
            errors.append(f"line {index}: missing fragment")
        if node.identity in seen_ids:
            errors.append(f"line {index}: duplicate account {node.identity}")
        seen_ids.add(node.identity)

    b64_path = out / "sub.b64"
    if not b64_path.is_file():
        errors.append("sub.b64 (base64) is missing")
    else:
        try:
            decoded = base64.b64decode(b64_path.read_text(encoding="ascii")).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sub.b64 is not valid base64: {exc}")
        else:
            if decoded != raw:
                errors.append("sub.b64 does not decode to sub.txt")

    if errors:
        for error in errors[:40]:
            print(f"VERIFY ERROR: {error}", file=sys.stderr)
    return errors


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "dist"
    errors = verify(out)
    if errors:
        return 1
    print(f"OK: {out} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
