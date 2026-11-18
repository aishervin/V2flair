/**
 * ☬SHΞN™ — UA-aware subscription endpoint.
 *
 * Same URL, two behaviours (exactly like the old Express `server.js`):
 *   • v2rayNG / NekoBox / Hiddify / Happ / sing-box ... -> base64 subscription
 *   • a browser (Accept: text/html)                     -> the demo page
 *
 * The static files are generated hourly by GitHub Actions:
 *   /sub.b64   base64 payload
 *   /sub.txt   plain, one node per line
 */

const CLIENT_RE =
  /(v2ray|v2rayng|sing-?box|nekobox|neko ?box|clash|mihomo|hiddify|happ|streisand|shadowrocket|quantumult|surge|stash|foxray|loon|sagernet|matsuri|v2box|kitsunebi|nekoray|xray|v2fly|hysteria|sfa|sfi|sft|sub-?link|okhttp|go-http-client|dart|python-requests|axios)/i;

const BASE_HEADERS = {
  "cache-control": "no-store, no-cache, must-revalidate",
  "access-control-allow-origin": "*",
};

export async function handleSubscription(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const ua = (request.headers.get("user-agent") || "").toLowerCase();
  const accept = (request.headers.get("accept") || "").toLowerCase();
  const force = url.searchParams.has("sub") || url.searchParams.get("format") === "base64";
  const isBrowser = accept.includes("text/html") && !CLIENT_RE.test(ua);

  if (isBrowser && !force) {
    const page = await env.ASSETS.fetch(new URL("/index.html", url));
    return new Response(page.body, {
      status: page.status,
      headers: {
        "content-type": "text/html; charset=utf-8",
        ...BASE_HEADERS,
      },
    });
  }

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
