"""Central configuration for the V2flair pipeline."""
from __future__ import annotations

import os

# --- Branding -------------------------------------------------------------
# Final remark is:  <flag emoji><BRAND>
# e.g.  🇹🇷®️SHΞN™ᴢᴇʀᴏ
BRAND = "\u00ae\ufe0fSH\u039eN\u2122\u1d22\u1d07\u0280\u1d0f"  # ®️SHΞN™ᴢᴇʀᴏ

# --- What we publish -------------------------------------------------------
# VLESS only by default (the pipeline targets curated VLESS collector repos).
ALLOWED_PROTOCOLS = tuple(
    p.strip().lower()
    for p in os.getenv("ALLOWED_PROTOCOLS", "vless").split(",")
    if p.strip()
)

# --- Output ----------------------------------------------------------------
DEFAULT_MAX_NODES = int(os.getenv("MAX_NODES", "200"))
HARD_MAX_NODES = 500

# --- Health thresholds (speed is kbit/s) -----------------------------------
MIN_SPEED_KBPS = float(os.getenv("MIN_SPEED_KBPS", "800"))   # ~100 KB/s
MIN_SPEED_FLOOR_KBPS = 300.0                                  # relax limit
MAX_LATENCY_MS = float(os.getenv("MAX_LATENCY_MS", "2500"))
MIN_STABILITY = 0.5          # at least 1 of 2 probes must succeed

# --- Network behaviour -----------------------------------------------------
FETCH_TIMEOUT = 25
FETCH_MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = "v2rayNG/1.9.5"

TCP_TIMEOUT = 2.0
TCP_CONCURRENCY = 400

PROBE_CONCURRENCY = 80
PROBE_TIMEOUT = 5.0
PROBE_ATTEMPTS = 1
PROBE_URLS = (
    "http://cp.cloudflare.com/generate_204",
    "http://www.gstatic.com/generate_204",
)

SPEED_URL = "https://speed.cloudflare.com/__down?bytes=524288"
SPEED_TIMEOUT = 15.0
SPEED_CONCURRENCY = 40

TRACE_URL = "https://1.1.1.1/cdn-cgi/trace"
TRACE_TIMEOUT = 5.0

XRAY_BATCH_SIZE = 120
XRAY_READY_TIMEOUT = 10.0
XRAY_BASE_PORT = 21000
TIME_BUDGET_SECONDS = int(os.getenv("TIME_BUDGET_SECONDS", "1500"))

# --- Safety ----------------------------------------------------------------
MIN_PUBLISH_NODES = 20
