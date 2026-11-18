#!/usr/bin/env bash
# Download the test binaries/databases (cached by GitHub Actions).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/bin"
CACHE="$ROOT/.cache"
mkdir -p "$BIN" "$CACHE"

# Pinned on purpose: Xray 26.x removed `allowInsecure` from tlsSettings and
# would refuse to start for nodes that rely on it. v25.x matches what most
# clients (v2rayNG, NekoBox) still ship.
XRAY_VERSION="${XRAY_VERSION:-v25.12.8}"
XRAY_ASSET="${XRAY_ASSET:-Xray-linux-64.zip}"

if [ ! -x "$BIN/xray" ]; then
  echo "downloading xray ${XRAY_VERSION} (${XRAY_ASSET})..."
  TMP="${TMPDIR:-/tmp}"
  curl -fsSL --retry 4 --retry-delay 2 -o "$TMP/xray.zip" \
    "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/${XRAY_ASSET}"
  unzip -o -q "$TMP/xray.zip" xray -d "$BIN"
  chmod +x "$BIN/xray"
fi
"$BIN/xray" version | head -n 1

# hysteria2 client for QUIC nodes (pinned, same reason as xray).
HYSTERIA_VERSION="${HYSTERIA_VERSION:-v2.6.5}"
HYSTERIA_ASSET="${HYSTERIA_ASSET:-hysteria-linux-amd64}"

if [ ! -x "$BIN/hysteria" ]; then
  echo "downloading hysteria ${HYSTERIA_VERSION} (${HYSTERIA_ASSET})..."
  curl -fsSL --retry 4 --retry-delay 2 -o "$BIN/hysteria" \
    "https://github.com/apernet/hysteria/releases/download/app/${HYSTERIA_VERSION}/${HYSTERIA_ASSET}"
  chmod +x "$BIN/hysteria"
fi
"$BIN/hysteria" version | head -n 1 || true

if [ ! -s "$CACHE/GeoLite2-Country.mmdb" ]; then
  echo "downloading GeoLite2 country db..."
  curl -fsSL --retry 3 --retry-delay 2 -o "$CACHE/GeoLite2-Country.mmdb" \
    "https://raw.githubusercontent.com/P3TERX/GeoLite.mmdb/download/GeoLite2-Country.mmdb" || true
fi
ls -lh "$CACHE/GeoLite2-Country.mmdb" 2>/dev/null || true
