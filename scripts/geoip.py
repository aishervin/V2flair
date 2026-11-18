"""Offline GeoIP fallback using the GeoLite2 country database."""
from __future__ import annotations

import ipaddress
import logging
import socket
from pathlib import Path
from typing import Optional

log = logging.getLogger("geoip")

try:  # optional dependency
    import maxminddb
except Exception:  # pragma: no cover - missing dependency is fine
    maxminddb = None  # type: ignore

DEFAULT_DB = Path(__file__).resolve().parent.parent / ".cache" / "GeoLite2-Country.mmdb"


class GeoIP:
    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self._reader = None
        self._ip_cache: dict[str, str] = {}

    def _open(self):
        if self._reader is None:
            if not (maxminddb and self.db_path.is_file()):
                return None
            try:
                self._reader = maxminddb.open_database(str(self.db_path))
            except Exception as exc:  # pragma: no cover
                log.warning("cannot open geoip db: %s", exc)
                return None
        return self._reader

    def ip_for(self, host: str) -> str:
        if host in self._ip_cache:
            return self._ip_cache[host]
        try:
            ipaddress.ip_address(host)
            self._ip_cache[host] = host
            return host
        except ValueError:
            pass
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except Exception:
            self._ip_cache[host] = ""
            return ""
        ip = ""
        for info in infos:
            candidate = info[4][0]
            if ":" not in candidate:  # prefer IPv4
                ip = candidate
                break
        if not ip and infos:
            ip = infos[0][4][0]
        self._ip_cache[host] = ip
        return ip

    def country(self, host: str) -> str:
        reader = self._open()
        if reader is None:
            return ""
        ip = self.ip_for(host)
        if not ip:
            return ""
        try:
            data = reader.get(ip)
        except Exception:
            return ""
        if not data:
            return ""
        return (
            data.get("country", {}).get("iso_code")
            or data.get("registered_country", {}).get("iso_code")
            or ""
        )

    def close(self) -> None:
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass
            self._reader = None


_default: Optional[GeoIP] = None


def get_geoip(db_path: str | Path = DEFAULT_DB) -> GeoIP:
    global _default
    if _default is None:
        _default = GeoIP(db_path)
    return _default
