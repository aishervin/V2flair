"""VLESS parsing, validation and normalisation.

Everything in this module is pure (no network) so it can be unit-tested
locally and reused by both the tester and the verifier.
"""
from __future__ import annotations

import base64
import ipaddress
import re
import uuid
from dataclasses import dataclass, field
from typing import Iterable, Optional
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from config import ALLOWED_PROTOCOLS, BRAND

URI_RE = re.compile(r"(?<![A-Za-z0-9+.\-])([a-zA-Z][a-zA-Z0-9+.\-]*)://[^\s\"'<>\\]+")

ALLOWED_NETWORKS = {
    "tcp": "tcp",
    "raw": "tcp",
    "ws": "ws",
    "websocket": "ws",
    "grpc": "grpc",
    "gun": "grpc",
    "httpupgrade": "httpupgrade",
    "xhttp": "xhttp",
    "splithttp": "splithttp",
    "h2": "h2",
    "http": "h2",
    "http2": "h2",
    "kcp": "kcp",
    "mkcp": "kcp",
}

BAD_TLDS = (".local", ".localhost", ".invalid", ".test", ".example", ".onion")
RESERVED_NAMES = {"localhost", "localhost.localdomain", "0.0.0.0", "::", "::1"}


@dataclass(slots=True)
class Node:
    uri: str                       # normalised vless:// URI, no fragment
    uid: str
    host: str
    port: int
    security: str = "none"         # none | tls | reality
    net: str = "tcp"
    sni: str = ""
    fp: str = ""
    pbk: str = ""
    sid: str = ""
    spx: str = ""
    flow: str = ""
    path: str = ""
    host_header: str = ""
    service_name: str = ""
    mode: str = ""
    alpn: str = ""
    header_type: str = ""
    allow_insecure: bool = False

    raw_remark: str = ""
    source: str = ""
    source_rank: int = 0

    # hysteria2
    kind: str = "vless"            # vless | hysteria2
    auth: str = ""
    obfs: str = ""
    obfs_password: str = ""
    pin: str = ""

    # test results
    tcp_ms: float = 0.0
    latency_ms: float = 0.0
    speed_kbps: float = 0.0
    ok: int = 0
    fail: int = 0
    country: str = ""
    flag: str = ""
    score: float = 0.0
    remark: str = ""

    @property
    def identity(self) -> str:
        """One account = one credential on one endpoint (ignores transport params)."""
        if self.kind == "hysteria2":
            return f"hy2|{self.auth}|{self.host.lower()}|{self.port}"
        return f"{self.uid}|{self.host.lower()}|{self.port}"

    @property
    def key(self) -> str:
        """Full semantic identity, catches param reordering / duplicate sources."""
        return "|".join(
            (
                self.kind,
                self.identity,
                self.obfs,
                self.obfs_password,
                self.pin,
                self.net,
                self.security,
                self.sni.lower(),
                self.path,
                self.host_header.lower(),
                self.pbk,
                self.sid,
                self.flow,
                self.service_name,
                self.mode,
            )
        )


# --- helpers --------------------------------------------------------------


def is_public_host(host: str) -> bool:
    if not host:
        return False
    host = host.strip().strip("[]").lower()
    if not host or host in RESERVED_NAMES:
        return False
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_global and not (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        )
    except ValueError:
        pass
    if host.endswith(BAD_TLDS):
        return False
    if "." not in host:
        return False
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9._-]*[a-z0-9])?", host))


def normalize_uuid(value: str) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        return None


def flag_for(country: str) -> str:
    cc = (country or "").strip().upper()
    if len(cc) != 2 or not cc.isalpha():
        return "\U0001F310"  # 🌐
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in cc)


def extract_flag_from_text(text: str) -> str:
    if not text:
        return ""
    for i in range(len(text) - 1):
        a, b = ord(text[i]), ord(text[i + 1])
        if 0x1F1E6 <= a <= 0x1F1FF and 0x1F1E6 <= b <= 0x1F1FF:
            return text[i : i + 2]
    return ""


def final_remark(node: Node) -> str:
    return f"{node.flag or flag_for(node.country)}{BRAND}"


# --- decoding -------------------------------------------------------------


def _try_b64(text: str) -> Optional[str]:
    raw = re.sub(r"\s+", "", text)
    if len(raw) < 32:
        return None
    raw = raw.replace("-", "+").replace("_", "/")
    raw += "=" * (-len(raw) % 4)
    try:
        decoded = base64.b64decode(raw, validate=True).decode("utf-8", "ignore")
    except Exception:
        return None
    return decoded if "://" in decoded else None


def _strip_wrappers(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("&amp;", "&").replace("\\u0026", "&").replace("\\/", "/")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith("//"):
            # subscription metadata, never a config
            if "://" not in s:
                continue
        lines.append(s)
    return "\n".join(lines)


def decode_payload(text: str) -> str:
    """Return the payload with base64 wrappers removed."""
    if not text:
        return ""
    cleaned = _strip_wrappers(text)
    if "://" in cleaned:
        return cleaned
    decoded = _try_b64(cleaned)
    return decoded or cleaned


def extract_uris(text: str) -> list[str]:
    payload = decode_payload(text)
    out: list[str] = []
    for match in URI_RE.finditer(payload):
        uri = match.group(0).rstrip(".,;)]}")
        out.append(uri)
    return out


# --- parsing --------------------------------------------------------------


def _clean_params(query: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        key = key.strip().lower()
        if key not in params:
            params[key] = value.strip()
    return params


def parse_uri(uri: str, source: str = "") -> Optional[Node]:
    uri = (uri or "").strip()
    if not uri:
        return None
    if uri.startswith("#") or uri.startswith("//"):
        return None

    # Some scraped links come HTML/JSON escaped.
    uri = uri.replace("&amp;", "&").replace("\\u0026", "&").replace("\\/", "/")

    try:
        parts = urlsplit(uri)
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_PROTOCOLS:
        return None
    if scheme in {"hysteria2", "hy2"}:
        return _parse_hysteria2(uri, source)
    if scheme != "vless":
        return None

    uid = normalize_uuid(unquote(parts.username or ""))
    if not uid:
        return None

    host = (parts.hostname or "").strip()
    try:
        port = parts.port
    except ValueError:
        return None
    if not host or not port or not 1 <= port <= 65535:
        return None
    if not is_public_host(host):
        return None

    params = _clean_params(parts.query)

    encryption = (params.get("encryption") or "none").lower()
    if encryption not in {"", "none"}:
        return None

    security = (params.get("security") or "none").lower()
    if security in {"", "none"}:
        security = "none"
    elif security == "xtls":
        security = "tls"
    if security not in {"none", "tls", "reality"}:
        return None

    raw_net = (params.get("type") or params.get("network") or "tcp").lower()
    net = ALLOWED_NETWORKS.get(raw_net)
    if not net:
        return None

    sni = params.get("sni") or params.get("peer") or ""
    if not sni and security in {"tls", "reality"} and not _is_ip(host):
        sni = host
    if security in {"tls", "reality"} and not sni:
        return None

    pbk = params.get("pbk") or params.get("publickey") or ""
    sid = params.get("sid") or params.get("shortid") or ""
    spx = params.get("spx") or params.get("spiderx") or "/"
    if security == "reality" and not pbk:
        return None

    flow = (params.get("flow") or "").lower()
    if not (net == "tcp" and security in {"tls", "reality"} and flow == "xtls-rprx-vision"):
        flow = ""

    header_type = (params.get("headertype") or "").lower()
    if header_type not in {"http", "none", ""}:
        header_type = ""

    path = params.get("path") or ""
    if net in {"ws", "httpupgrade", "xhttp", "splithttp", "h2"} and not path:
        path = "/"

    service_name = params.get("servicename") or ""
    if net == "grpc" and not service_name:
        service_name = path.lstrip("/")

    host_header = params.get("host") or ""
    mode = (params.get("mode") or "").lower()
    alpn = params.get("alpn") or ""
    fp = (params.get("fp") or "").lower()
    if security == "reality" and not fp:
        fp = "chrome"

    allow_insecure = str(params.get("allowinsecure") or params.get("insecure") or "").lower() in {
        "1", "true", "yes"
    }

    # Rebuild a clean query string with canonical parameter names. Unknown
    # params are preserved on purpose: we test and publish the very same URI.
    handled = {
        "remarks", "remark", "network", "peer", "publickey", "shortid",
        "spiderx", "headertype", "servicename", "allowinsecure", "insecure",
        "host", "path", "mode", "alpn", "fp", "sni", "pbk", "sid", "spx",
        "flow", "encryption", "security", "type",
    }
    out: dict[str, str] = {k: v for k, v in params.items() if k not in handled}
    out["encryption"] = "none"
    out["security"] = security
    out["type"] = net
    if security != "none":
        out["sni"] = sni
        if fp:
            out["fp"] = fp
        if alpn:
            out["alpn"] = alpn
    if security == "reality":
        out["pbk"] = pbk
        if sid:
            out["sid"] = sid
        if spx:
            out["spx"] = spx
    if flow:
        out["flow"] = flow
    if net == "tcp" and header_type == "http":
        out["headerType"] = "http"
        out["path"] = path or "/"
        if host_header:
            out["host"] = host_header
    elif net in {"ws", "httpupgrade", "xhttp", "splithttp", "h2"}:
        out["path"] = path or "/"
        if host_header:
            out["host"] = host_header
        if mode:
            out["mode"] = mode
    elif net == "grpc":
        if service_name:
            out["serviceName"] = service_name
        if mode:
            out["mode"] = mode
    if allow_insecure and security == "tls":
        out["allowInsecure"] = "1"

    host_fmt = f"[{host}]" if ":" in host else host
    query = urlencode(out, quote_via=quote, safe="")
    base = f"vless://{uid}@{host_fmt}:{port}?{query}"

    node = Node(
        uri=base,
        uid=uid,
        host=host.lower(),
        port=port,
        security=security,
        net=net,
        sni=sni,
        fp=fp,
        pbk=pbk,
        sid=sid,
        spx=spx,
        flow=flow,
        path=path,
        host_header=host_header,
        service_name=service_name,
        mode=mode,
        alpn=alpn,
        header_type=header_type,
        allow_insecure=allow_insecure,
        raw_remark=unquote(parts.fragment or ""),
        source=source,
    )
    node.flag = extract_flag_from_text(node.raw_remark)
    return node


def _parse_hysteria2(uri: str, source: str) -> Optional[Node]:
    """Parse/normalise a hysteria2:// (hy2://) URI.

    Format: hysteria2://[user:pass@]host:port?insecure=1&sni=..&obfs=salamander
            &obfs-password=..&pinSHA256=..#remark
    """
    try:
        parts = urlsplit(uri)
    except ValueError:
        return None

    auth = unquote(parts.username or "")
    if parts.password:
        auth = f"{auth}:{unquote(parts.password)}"
    auth = auth.strip()
    if not auth:
        return None

    host = (parts.hostname or "").strip()
    try:
        port = parts.port
    except ValueError:
        return None
    if not host or not port or not 1 <= port <= 65535:
        return None
    if not is_public_host(host):
        return None

    params = _clean_params(parts.query)

    sni = (params.get("sni") or params.get("peer") or "").strip()
    if not sni and not _is_ip(host):
        sni = host

    allow_insecure = str(params.get("insecure") or params.get("allowinsecure") or "").lower() in {
        "1", "true", "yes"
    }

    obfs = (params.get("obfs") or "").lower()
    if obfs and obfs != "salamander":
        obfs = ""
    obfs_password = params.get("obfs-password") or params.get("obfspassword") or ""
    if obfs and not obfs_password:
        obfs = ""

    pin = (params.get("pinsha256") or params.get("pin") or "").strip()
    alpn = (params.get("alpn") or "").strip()

    handled = {
        "remarks", "remark", "sni", "peer", "insecure", "allowinsecure",
        "obfs", "obfs-password", "obfspassword", "pinsha256", "pin", "alpn",
    }
    out: dict[str, str] = {k: v for k, v in params.items() if k not in handled}
    if allow_insecure:
        out["insecure"] = "1"
    if sni:
        out["sni"] = sni
    if obfs:
        out["obfs"] = obfs
        out["obfs-password"] = obfs_password
    if pin:
        out["pinSHA256"] = pin
    if alpn:
        out["alpn"] = alpn

    host_fmt = f"[{host}]" if ":" in host else host
    query = urlencode(out, quote_via=quote, safe="")
    node = Node(
        uri=f"hysteria2://{quote(auth, safe='')}@{host_fmt}:{port}?{query}",
        uid=auth,
        auth=auth,
        kind="hysteria2",
        host=host.lower(),
        port=port,
        security="tls",
        net="quic",
        sni=sni,
        alpn=alpn,
        obfs=obfs,
        obfs_password=obfs_password,
        pin=pin,
        allow_insecure=allow_insecure,
        raw_remark=unquote(parts.fragment or ""),
        source=source,
    )
    node.flag = extract_flag_from_text(node.raw_remark)
    return node


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def parse_many(texts: Iterable[tuple[str, str]]) -> tuple[list[Node], dict[str, int]]:
    """Parse (source, text) pairs. Returns nodes + rejection statistics."""
    nodes: list[Node] = []
    stats = {"uris": 0, "accepted": 0, "rejected": 0}
    for rank, (source, text) in enumerate(texts):
        for uri in extract_uris(text):
            stats["uris"] += 1
            node = parse_uri(uri, source)
            if node is None:
                stats["rejected"] += 1
                continue
            node.source_rank = rank
            if not node.flag:
                node.flag = extract_flag_from_text(node.raw_remark)
            stats["accepted"] += 1
            nodes.append(node)
    return nodes, stats


def dedupe(nodes: Iterable[Node]) -> list[Node]:
    """Remove exact and semantic duplicates, keeping the first occurrence."""
    seen: set[str] = set()
    out: list[Node] = []
    for node in nodes:
        key = node.key
        if key in seen:
            continue
        seen.add(key)
        out.append(node)
    return out


def publish_uri(node: Node) -> str:
    return f"{node.uri}#{quote(final_remark(node), safe='')}"
