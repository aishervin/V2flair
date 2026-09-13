#!/usr/bin/env python3
"""
V2flair TCP Latency Tester & GeoIP Filter Pipeline
- Fetches proxy configs (VLESS, VMess, Hysteria2, hy2)
- Tests TCP handshake ping concurrently
- Discards offline / timed-out servers
- Looks up GeoIP country code via https://api.ip.sb/geoip
- Injects flag emoji into remark: ®️SHΞN™ᴢᴇʀᴏ{FLAG}T.me/Shervini
- Sorts by lowest ping and outputs to clean_sub.txt
- Can run once or every 30 minutes in a background loop
"""

import asyncio
import base64
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

REMARK_PREFIX = "®️SHΞN™ᴢᴇʀᴏ"
REMARK_SUFFIX = "T.me/Shervini"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean_sub.txt")
MAX_ALIVE_OUTPUT = 1000
TCP_TIMEOUT_SECONDS = 2.5
CONCURRENCY_LIMIT = 50

GEOIP_CACHE: Dict[str, str] = {}

FALLBACK_SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/mix",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hy2",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vmess",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
    "https://raw.githubusercontent.com/MrPooyaCou/V2root/main/HY2.txt",
    "https://raw.githubusercontent.com/MrPooyaCou/V2root/main/VMess.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/hysteria2.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/vless.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/aishervin/subfine/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/aishervin/subfine/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/aishervin/v2ray/refs/heads/main/Sub.json",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/refs/heads/main/all/configs.txt",
    "https://raw.githubusercontent.com/iboxz/free-v2ray-collector/main/main/vless.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS.txt",
    "https://raw.githubusercontent.com/F0rc3Run/F0rc3Run/refs/heads/main/splitted-by-protocol/vless.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/refs/heads/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/Sub2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/Sub3.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
    "https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/refs/heads/main/subscriptions/all.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/refs/heads/main/v2ray.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/refs/heads/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/ThomasJasperthecat/sub/refs/heads/main/sublist1.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/vless.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/reality.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Sub1.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/Config_jo.txt",
    "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/Config_no_cf.txt",
    "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vless.txt",
    "https://raw.githubusercontent.com/balochscript/free-vpn-configs/gh-pages/subscription-realdelay.txt",
    "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vless_iran.txt"
];


def country_code_to_flag(code: Optional[str]) -> str:
    """Converts a two-letter ISO country code into Unicode Flag Emoji."""
    if not code or len(code) != 2:
        return "🌐"
    code = code.upper()
    if not (code[0].isalpha() and code[1].isalpha()):
        return "🌐"
    return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))

def make_remark(flag_emoji: str) -> str:
    return f"{REMARK_PREFIX}{flag_emoji}{REMARK_SUFFIX}"

def safe_b64decode(data: str) -> str:
    data = data.strip().replace('-', '+').replace('_', '/')
    pad = len(data) % 4
    if pad:
        data += '=' * (4 - pad)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore')
    except Exception:
        return ""

def safe_b64encode(data: str) -> str:
    return base64.b64encode(data.encode('utf-8')).decode('ascii')

class ConfigItem:
    def __init__(self, protocol: str, host: str, port: int, original_uri: str, vmess_json: Optional[dict] = None, base_uri: str = ""):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.original_uri = original_uri
        self.vmess_json = vmess_json
        self.base_uri = base_uri
        self.ping_ms: float = 99999.0
        self.country_code: str = ""
        self.flag: str = "🌐"

    def format_with_remark(self, remark: str) -> str:
        if self.protocol == 'vmess' and self.vmess_json:
            copied = dict(self.vmess_json)
            copied['ps'] = remark
            json_str = json.dumps(copied, ensure_ascii=False)
            return 'vmess://' + safe_b64encode(json_str)
        else:
            base = self.base_uri or self.original_uri.split('#')[0]
            return f"{base}#{urllib.parse.quote(remark)}"

def parse_config(uri: str) -> Optional[ConfigItem]:
    uri = uri.strip()
    if not uri:
        return None

    if uri.startswith('vmess://'):
        b64_part = uri[8:].strip()
        decoded = safe_b64decode(b64_part)
        if not decoded:
            return None
        try:
            data = json.loads(decoded)
            host = data.get('add', '').strip()
            port = int(data.get('port', 443))
            if host and port > 0:
                return ConfigItem(protocol='vmess', host=host, port=port, original_uri=uri, vmess_json=data)
        except Exception:
            return None
        return None

    # Handle vless://, hysteria2://, hy2://
    m = re.match(r'^(vless|hysteria2|hy2)://([^/?#]+)(.*)$', uri, re.IGNORECASE)
    if not m:
        return None

    protocol = m.group(1).lower()
    auth_host_port = m.group(2)
    rest = m.group(3)

    base_uri = f"{protocol}://{auth_host_port}{rest}".split('#')[0]

    # Extract host and port
    if '@' in auth_host_port:
        host_port = auth_host_port.split('@')[-1]
    else:
        host_port = auth_host_port

    if ':' in host_port:
        parts = host_port.split(':')
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            port = 443
    else:
        host = host_port
        port = 443

    if host:
        return ConfigItem(protocol=protocol, host=host, port=port, original_uri=uri, base_uri=base_uri)

    return None

async def test_tcp_ping(item: ConfigItem, timeout: float = TCP_TIMEOUT_SECONDS) -> bool:
    """Performs TCP connect handshake test to measure latency in ms."""
    t_start = time.perf_counter()
    try:
        # Resolve hostname or IP asynchronously
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(item.host, item.port),
            timeout=timeout
        )
        t_end = time.perf_counter()
        item.ping_ms = round((t_end - t_start) * 1000, 1)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False

async def fetch_geoip(host: str, session_semaphore: asyncio.Semaphore) -> str:
    """Queries https://api.ip.sb/geoip to get country code with caching."""
    if host in GEOIP_CACHE:
        return GEOIP_CACHE[host]

    async with session_semaphore:
        # Check cache again
        if host in GEOIP_CACHE:
            return GEOIP_CACHE[host]

        url = f"https://api.ip.sb/geoip/{host}"
        loop = asyncio.get_running_loop()

        def do_req():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get("country_code", "")
            return ""

        try:
            code = await loop.run_in_executor(None, do_req)
            if code:
                GEOIP_CACHE[host] = code
                return code
        except Exception:
            pass

    return ""

async def fetch_source(url: str) -> str:
    loop = asyncio.get_running_loop()
    def _fetch():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6.0) as r:
            return r.read().decode('utf-8', errors='ignore')
    try:
        return await loop.run_in_executor(None, _fetch)
    except Exception:
        return ""

async def collect_raw_configs(worker_url: Optional[str] = None) -> List[str]:
    raw_lines = []
    
    # If worker URL is provided, fetch from it first
    if worker_url:
        print(f"[*] Fetching from worker endpoint: {worker_url}")
        content = await fetch_source(worker_url)
        if content:
            # Check if base64 encoded
            decoded = safe_b64decode(content)
            if '://' in decoded:
                raw_lines.extend(decoded.splitlines())
            else:
                raw_lines.extend(content.splitlines())

    if len(raw_lines) < 50:
        print("[*] Fetching from upstream source repositories...")
        tasks = [fetch_source(u) for u in FALLBACK_SOURCES]
        results = await asyncio.gather(*tasks)
        for res in results:
            if not res:
                continue
            decoded = safe_b64decode(res)
            if '://' in decoded:
                raw_lines.extend(decoded.splitlines())
            else:
                raw_lines.extend(res.splitlines())

    # Regex search for configs in aggregated text
    combined = "\n".join(raw_lines)
    matches = re.findall(r'(?:vless|vmess|hysteria2|hy2)://[^\s"\'<>]+', combined, re.IGNORECASE)
    print(f"[*] Extracted {len(matches)} total candidate configs.")
    return matches

async def run_pipeline(worker_url: Optional[str] = None):
    print("=" * 60)
    print("🚀 Starting V2flair Tester & GeoIP Filter Pipeline")
    print(f"⏰ Local time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    raw_configs = await collect_raw_configs(worker_url)
    
    # Parse and deduplicate
    parsed_items: List[ConfigItem] = []
    seen_keys = set()
    for uri in raw_configs:
        item = parse_config(uri)
        if not item:
            continue
        key = f"{item.protocol}:{item.host}:{item.port}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        parsed_items.append(item)

    print(f"[*] Unique configs to test: {len(parsed_items)}")
    if not parsed_items:
        print("[!] No configs found to test.")
        return

    # Concurrently test TCP ping
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    alive_items: List[ConfigItem] = []

    async def test_worker(cfg: ConfigItem):
        async with sem:
            ok = await test_tcp_ping(cfg)
            if ok:
                alive_items.append(cfg)

    print(f"[*] Testing TCP ping with concurrency {CONCURRENCY_LIMIT}...")
    await asyncio.gather(*(test_worker(c) for c in parsed_items))

    # Sort alive items by ping (lowest ping first)
    alive_items.sort(key=lambda x: x.ping_ms)
    print(f"[+] Alive & healthy servers found: {len(alive_items)} / {len(parsed_items)}")

    if not alive_items:
        print("[!] No responsive servers passed the TCP handshake test.")
        return

    # Trim to max output
    selected = alive_items[:MAX_ALIVE_OUTPUT]

    # Resolve GeoIP for alive servers
    print(f"[*] Resolving GeoIP via api.ip.sb for top {len(selected)} alive servers...")
    geoip_sem = asyncio.Semaphore(10)
    
    async def resolve_item_geoip(cfg: ConfigItem):
        code = await fetch_geoip(cfg.host, geoip_sem)
        cfg.country_code = code
        cfg.flag = country_code_to_flag(code)

    await asyncio.gather(*(resolve_item_geoip(c) for c in selected))

    # Format output configs
    final_configs = []
    for c in selected:
        remark = make_remark(c.flag)
        final_uri = c.format_with_remark(remark)
        final_configs.append(final_uri)

    # Save to clean_sub.txt
    output_content = "\n".join(final_configs)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"✅ Successfully wrote {len(final_configs)} clean tested configs to {OUTPUT_FILE}")
    if final_configs:
        print(f"🔍 Top node ping: {selected[0].ping_ms}ms, Flag: {selected[0].flag}, Protocol: {selected[0].protocol}")

async def main():
    worker_url = None
    loop_interval = 0

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--worker' and i + 1 < len(args):
            worker_url = args[i + 1]
            i += 2
        elif args[i] == '--loop':
            loop_interval = 1800 # 30 minutes
            if i + 1 < len(args) and args[i + 1].isdigit():
                loop_interval = int(args[i + 1])
                i += 1
            i += 1
        else:
            i += 1

    if loop_interval > 0:
        print(f"[*] Running in daemon loop mode every {loop_interval} seconds (30m)...")
        while True:
            try:
                await run_pipeline(worker_url)
            except Exception as e:
                print(f"[!] Error in pipeline execution: {e}")
            print(f"[*] Sleeping for {loop_interval}s until next test cycle...")
            await asyncio.sleep(loop_interval)
    else:
        await run_pipeline(worker_url)

if __name__ == '__main__':
    asyncio.run(main())
