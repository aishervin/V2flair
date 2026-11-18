"""Build a single Xray config with N SOCKS inbounds (one per node)."""
from __future__ import annotations

from typing import Iterable

from parse import Node

OUTBOUND_PROTOCOLS = {"vless"}


def _stream_settings(node: Node) -> dict:
    stream: dict = {"network": node.net, "security": node.security}

    if node.security == "tls":
        tls: dict = {"serverName": node.sni, "allowInsecure": True}
        if node.fp:
            tls["fingerprint"] = node.fp
        if node.alpn:
            tls["alpn"] = [a for a in node.alpn.split(",") if a]
        stream["tlsSettings"] = tls
    elif node.security == "reality":
        stream["realitySettings"] = {
            "serverName": node.sni,
            "fingerprint": node.fp or "chrome",
            "publicKey": node.pbk,
            "shortId": node.sid,
            "spiderX": node.spx or "/",
        }

    net = node.net
    if net == "ws":
        ws: dict = {"path": node.path or "/"}
        if node.host_header:
            ws["headers"] = {"Host": node.host_header}
        stream["wsSettings"] = ws
    elif net == "grpc":
        stream["grpcSettings"] = {
            "serviceName": node.service_name,
            "multiMode": node.mode == "multi",
        }
    elif net == "httpupgrade":
        hu: dict = {"path": node.path or "/"}
        if node.host_header:
            hu["host"] = node.host_header
        stream["httpupgradeSettings"] = hu
    elif net in {"xhttp", "splithttp"}:
        xh: dict = {"path": node.path or "/"}
        if node.host_header:
            xh["host"] = node.host_header
        if node.mode:
            xh["mode"] = node.mode
        stream["xhttpSettings" if net == "xhttp" else "splithttpSettings"] = xh
    elif net == "h2":
        h2: dict = {"path": node.path or "/"}
        if node.host_header:
            h2["host"] = [h.strip() for h in node.host_header.split(",") if h.strip()]
        stream["httpSettings"] = h2
    elif net == "tcp" and node.header_type == "http":
        stream["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {
                    "path": [node.path or "/"],
                    "headers": {"Host": [node.host_header]} if node.host_header else {},
                },
            }
        }

    return stream


def outbound(node: Node, tag: str) -> dict:
    user: dict = {"id": node.uid, "encryption": "none"}
    if node.flow:
        user["flow"] = node.flow
    return {
        "tag": tag,
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": node.host,
                    "port": node.port,
                    "users": [user],
                }
            ]
        },
        "streamSettings": _stream_settings(node),
    }


def build_config(nodes: Iterable[Node], ports: list[int]) -> dict:
    nodes = list(nodes)
    assert len(nodes) == len(ports), "one port per node is required"

    inbounds = []
    outbounds = []
    rules = []
    for idx, (node, port) in enumerate(zip(nodes, ports)):
        in_tag = f"in{idx}"
        out_tag = f"out{idx}"
        inbounds.append(
            {
                "tag": in_tag,
                "listen": "127.0.0.1",
                "port": port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False},
            }
        )
        outbounds.append(outbound(node, out_tag))
        rules.append(
            {"type": "field", "inboundTag": [in_tag], "outboundTag": out_tag}
        )

    outbounds.append({"tag": "direct", "protocol": "freedom"})
    return {
        "log": {"loglevel": "error"},
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {"domainStrategy": "AsIs", "rules": rules},
    }
