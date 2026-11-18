/**
 * ☬SHΞN™ — Cloudflare Pages advanced mode worker (no wrangler needed).
 *
 * Cloudflare Pages picks up `_worker.js` from the repo root automatically.
 * One URL, two behaviours (same as the old server.js):
 *
 *   https://subshen.pages.dev/            browser -> index.html (demo + redirect)
 *   https://subshen.pages.dev/            client  -> base64 subscription
 *   https://subshen.pages.dev/sub         same dual behaviour
 *   https://subshen.pages.dev/api/sub     same
 *   https://subshen.pages.dev/sub.b64     raw base64
 *   https://subshen.pages.dev/sub.txt     plain text, one node per line
 */

const CLIENT_RE =
  /(v2ray|v2rayng|sing-?box|nekobox|neko ?box|clash|mihomo|hiddify|happ|streisand|shadowrocket|quantumult|surge|stash|foxray|loon|sagernet|matsuri|v2box|kitsunebi|nekoray|xray|v2fly|hysteria|sfa|sfi|sft|sub-?link|okhttp|go-http-client|dart|python-requests|axios)/i;

const SUB_PATHS = new Set(["/", "/sub", "/api/sub"]);

const BASE_HEADERS = {
  "cache-control": "no-store, no-cache, must-revalidate",
  "access-control-allow-origin": "*",
};

async function subscription(request, env, url) {
  const asset = await env.ASSETS.fetch(new URL("/sub.b64", url));
  if (!asset.ok) {
    return new Response("subscription is being built, retry in a minute\n", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", ...BASE_HEADERS },
    });
  }
  const payload = (await asset.text()).trim();
  return new Response(payload + "\n", {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "profile-update-interval": "1",
      "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
      ...BASE_HEADERS,
    },
  });
}

async function page(request, env, url) {
  const asset = await env.ASSETS.fetch(new URL("/index.html", url));
  return new Response(asset.body, {
    status: asset.status,
    headers: { "content-type": "text/html; charset=utf-8", ...BASE_HEADERS },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.length > 1 ? url.pathname.replace(/\/+$/, "") : "/";

    if (!SUB_PATHS.has(path)) {
      return env.ASSETS.fetch(request);
    }

    const ua = (request.headers.get("user-agent") || "").toLowerCase();
    const accept = (request.headers.get("accept") || "").toLowerCase();
    const force = url.searchParams.has("sub") || url.searchParams.get("format") === "base64";
    const isBrowser = accept.includes("text/html") && !CLIENT_RE.test(ua);

    if (isBrowser && !force) {
      return page(request, env, url);
    }
    return subscription(request, env, url);
  },
};
