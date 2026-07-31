/**
 * Exclusive ☬SHΞN™
 * Vless Advanced Filter + /24 Expander
 * Routes:
 *   /          → Base64 subscription (original logic)
 *   /extender  → Plain text expanded configs from duplicate groups
 */

// ==================== تابع دریافت کانفیگ از خودمان ====================
async function fetchOwnConfigs() {
    const response = await fetch('https://subshen.pages.dev/?sub=1', {
        headers: { 'User-Agent': 'v2ray' }
    });
    if (!response.ok) throw new Error(`Failed to fetch configs: ${response.status}`);
    const base64Text = await response.text();
    return atob(base64Text);
}

// ==================== تابع تولید کانفیگ‌های گسترش‌یافته ====================
async function generateExpandedConfigs() {
    const configsText = await fetchOwnConfigs();
    const matches = configsText.match(/vless:\/\/[^\s"'<>]+/gim) || [];

    function parseVless(uri) {
        try {
            const u = new URL(uri);
            return {
                uuid: u.username,
                host: u.hostname,
                port: parseInt(u.port) || 443,
                params: new URLSearchParams(u.search)
            };
        } catch { return null; }
    }

    function getGroupKey(parsed) {
        const { uuid, host, params } = parsed;
        const p = Object.fromEntries(params.entries());
        const exclude = ['sid', 'mode', 'alpn', 'insecure', 'allowInsecure'];
        for (const k of exclude) delete p[k];
        const sorted = Object.keys(p).sort().reduce((obj, k) => {
            obj[k] = p[k];
            return obj;
        }, {});
        return JSON.stringify({ uuid, host, ...sorted });
    }

    const groups = new Map();
    for (const uri of matches) {
        const parsed = parseVless(uri);
        if (!parsed) continue;
        const key = getGroupKey(parsed);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(parsed);
    }

    const duplicateGroups = [];
    for (const [key, items] of groups) {
        if (items.length >= 2) duplicateGroups.push(items);
    }

    // فقط ۵ گروه اول (در عمل به این تعداد نمی‌رسه، ولی برای احتیاط)
    const limitedGroups = duplicateGroups.slice(0, 5);
    if (limitedGroups.length === 0) return '# No duplicate groups found.';

    let allExpanded = [];
    for (const group of limitedGroups) {
        const base = group[0];
        const parts = base.host.split('.');
        if (parts.length !== 4) continue;
        const prefix = parts.slice(0, 3).join('.');
        for (let i = 0; i <= 255; i++) {
            const newHost = `${prefix}.${i}`;
            const params = new URLSearchParams(base.params);
            const search = params.toString();
            allExpanded.push(
                `vless://${base.uuid}@${newHost}:${base.port}${search ? '?'+search : ''}#${encodeURIComponent('☬SH℮N™ /24 '+prefix+'.'+i)}`
            );
        }
    }

    return allExpanded.length ? allExpanded.join('\n') : '# No valid IP ranges found.';
}

// ==================== هندلر اصلی ====================
export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        const path = url.pathname;

        // ========== مسیر /extender ==========
        if (path === '/extender') {
            if (request.method !== 'GET') {
                return new Response('Method Not Allowed', { status: 405 });
            }
            try {
                const expanded = await generateExpandedConfigs();
                return new Response(expanded, {
                    status: 200,
                    headers: {
                        'Content-Type': 'text/plain; charset=utf-8',
                        'Cache-Control': 'no-store, no-cache, must-revalidate'
                    }
                });
            } catch (err) {
                return new Response('Error: ' + err.message, { status: 500 });
            }
        }

        // ========== مسیر اصلی (ساب‌لینک) ==========
        const accept = request.headers.get('Accept') || '';
        const userAgent = (request.headers.get('User-Agent') || '').toLowerCase();

        const isBrowser = accept.includes('text/html') &&
                          !userAgent.includes('v2ray') &&
                          !userAgent.includes('sing-box') &&
                          !userAgent.includes('nekobox') &&
                          !userAgent.includes('clash') &&
                          !userAgent.includes('vless') &&
                          !userAgent.includes('vmess');

        if (isBrowser && !url.searchParams.has('sub')) {
            return new Response('☬SHΞN™ Subnet Detector - Use /extender for expanded configs', {
                status: 200,
                headers: { 'Content-Type': 'text/html' }
            });
        }

        // ---------- جمع‌آوری کانفیگ‌ها از منابع ----------
        const SOURCES = [
            "https://raw.githubusercontent.com/aishervin/v2ray/refs/heads/main/Sub.json",
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
            "https://raw.githubusercontent.com/pytimusprime/FreeV2ray/refs/heads/main/all_servers.txt",
            "https://raw.githubusercontent.com/ThomasJasperthecat/sub/refs/heads/main/sublist1.txt",
            "https://raw.githubusercontent.com/masir-sefid/Sub/refs/heads/main/@Masir_Sefid.txt",
            "https://raw.githubusercontent.com/masir-sefid/Sub/refs/heads/main/Telegram-Channel-@Masir_Sefid.txt",
            "https://raw.githubusercontent.com/AmyraxVPN-Main/AmyraxVPN/refs/heads/main/AmyraxVPN.txt",
            "https://raw.githubusercontent.com/MahsaNetConfigTopic/config/refs/heads/main/xray_final.txt",
            "https://raw.githubusercontent.com/barry-far/V2ray-config/refs/heads/main/All_Configs_base64_Sub.txt",
            "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/configs.txt",
            "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/vless.txt",
            "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/reality.txt",
            "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt",
            "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
            "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Sub1.txt",
            "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
            "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt",
            "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/Config_jo.txt",
            "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/Config_no_cf.txt"
        ];

        let combinedData = "";
        const fetchPromises = SOURCES.map(async (src) => {
            try {
                const resp = await fetch(src, {
                    headers: { "User-Agent": "Mozilla/5.0" }
                });
                if (resp.ok) {
                    const text = await resp.text();
                    combinedData += '\n' + text;
                }
            } catch (e) {}
        });
        await Promise.all(fetchPromises);

        // رمزگشایی خطوط بیس۶۴
        const lines = combinedData.split(/\r?\n/);
        for (const line of lines) {
            const s = line.trim();
            if (s.length > 50 && !s.includes('://') && /^[A-Za-z0-9+/=_-]+$/.test(s)) {
                try {
                    const decoded = atob(s.replace(/-/g, '+').replace(/_/g, '/'));
                    if (decoded.includes('://')) combinedData += '\n' + decoded;
                } catch (e) {}
            }
        }

        const regex = /vless:\/\/[^\s"'<>]+/gim;
        const matches = combinedData.match(regex) || [];

        // ---------- امتیازدهی و فیلتر ----------
        const REMARK_TAG = "☬SHΞN™  Ai core worker";
        const MAX_OUTPUT = 3500;

        const uniqueConfigsMap = new Map();

        for (let uri of matches) {
            try {
                const u = new URL(uri);
                const host = u.hostname;
                const port = parseInt(u.port) || 443;
                const params = new URLSearchParams(u.search);

                let net = (params.get('type') || 'tcp').toLowerCase();
                let security = (params.get('security') || '').toLowerCase();
                let flow = (params.get('flow') || '').toLowerCase();

                const allowedNets = ['ws', 'grpc', 'tcp', 'xhttp'];
                const allowedSec = ['tls', 'reality', 'xtls', 'none', ''];

                if (!allowedNets.includes(net) && !allowedSec.includes(security)) continue;
                if (!security) security = 'none';

                const key = `${host}|${port}|${net}`;

                let score = 40;
                if (security === 'reality') score += 50;
                else if (security === 'tls' || security === 'xtls') score += 20;
                if (net === 'grpc' || net === 'xhttp') score += 25;
                else if (net === 'ws') score += 20;
                else if (net === 'tcp' && flow === 'xtls-rprx-vision') score += 25;
                if ([443, 8443, 2096, 2087, 2053].includes(port)) score += 10;

                const existing = uniqueConfigsMap.get(key);
                if (!existing || score > existing.score) {
                    uniqueConfigsMap.set(key, { uri: uri.split('#')[0], score });
                }
            } catch (e) {}
        }

        const sortedConfigs = Array.from(uniqueConfigsMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, MAX_OUTPUT)
            .map(item => item.uri + '#' + encodeURIComponent(REMARK_TAG));

        const finalPayload = sortedConfigs.join('\n');
        const b64Payload = btoa(unescape(encodeURIComponent(finalPayload)));

        return new Response(b64Payload, {
            status: 200,
            headers: {
                "Content-Type": "text/plain; charset=utf-8",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Profile-Update-Interval": "6",
                "Subscription-Userinfo": "upload=0; download=0; total=10737418240000; expire=0"
            }
        });
    }
};
