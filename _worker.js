/**
 * Exclusive ☬SHΞN™ made
 * Vless Advanced Filter, Aggregator & Scorer
 */

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        const accept = request.headers.get('Accept') || '';
        const userAgent = (request.headers.get('User-Agent') || '').toLowerCase();
        
        // تشخیص هوشمند: آیا ریکوئست از مرورگر اومده یا کلاینت V2ray؟
        const isBrowser = accept.includes('text/html') && 
                          !userAgent.includes('v2ray') && 
                          !userAgent.includes('sing-box') &&
                          !userAgent.includes('nekobox') &&
                          !userAgent.includes('clash') &&
                          !userAgent.includes('vless');

        // اگر مرورگر بود، کلودفلر رو هدایت می‌کنیم تا فایل index.html که در ریپازیتوری هست رو نشون بده
        if (isBrowser && !url.searchParams.has('sub')) {
            return env.ASSETS.fetch(request);
        }

        // ==========================================
        // شروع لاجیک جمع‌آوری و فیلتر کانفیگ‌ها
        // ==========================================

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

        const REMARK_TAG = "☬SHΞN™  subshen.pages.dev";
        const MAX_OUTPUT = 3000;

        function safeAtobUnicode(str) {
            try {
                let s = str.trim();
                s = s.replace(/-/g, "+").replace(/_/g, "/");
                const pad = s.length % 4;
                if (pad) s += "=".repeat(4 - pad);
                return atob(s);
            } catch (e) {
                return str; 
            }
        }

        let combinedData = "";

        const fetchPromises = SOURCES.map(async (url) => {
            try {
                const response = await fetch(url, {
                    headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
                    cf: { cacheTtl: 3600 } 
                });
                if (response.ok) {
                    const text = await response.text();
                    combinedData += '\n' + text;
                }
            } catch (err) {}
        });

        await Promise.all(fetchPromises);

        const lines = combinedData.split(/\r?\n/);
        for (let line of lines) {
            let s = line.trim();
            if (s.length > 50 && !s.includes('://') && /^[A-Za-z0-9+/=_-]+$/.test(s)) {
                try {
                    const decoded = safeAtobUnicode(s);
                    if (decoded.includes('://')) combinedData += '\n' + decoded;
                } catch (e) {}
            }
        }

        const regex = /(vless):\/\/[^\s"'<>]+/gim;
        const matches = combinedData.match(regex) || [];
        const uniqueConfigsMap = new Map();

        for (let uri of matches) {
            try {
                const lowUri = uri.toLowerCase();
                const fakeUrlStr = 'http://' + lowUri.slice(8);
                const fakeUrl = new URL(fakeUrlStr);
                
                const port = parseInt(fakeUrl.port) || 443;
                const params = new URLSearchParams(fakeUrl.search);
                
                const net = (params.get('type') || params.get('mode') || 'tcp').toLowerCase();
                const security = (params.get('security') || '').toLowerCase();

                const allowedNets = ['ws', 'grpc', 'tcp', 'http', 'xhttp'];
                const allowedSec = ['tls', 'reality', 'tcp', 'xtls'];

                if (!allowedNets.includes(net) && !allowedSec.includes(security)) {
                    continue; 
                }

                const key = `${fakeUrl.hostname}|${port}|${net}`;

                let score = 50;
                if (security === 'reality') score += 30;
                else if (security === 'tls' || security === 'xtls') score += 20;
                
                if (['grpc', 'xhttp', 'ws'].includes(net)) score += 15;
                if ([443, 8443, 2053, 2083].includes(port)) score += 15;

                const existing = uniqueConfigsMap.get(key);
                if (!existing || score > existing.score) {
                    uniqueConfigsMap.set(key, { uri: uri.trim(), score: score });
                }
            } catch (e) {}
        }

        const sortedConfigs = Array.from(uniqueConfigsMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, MAX_OUTPUT)
            .map(item => {
                const baseUri = item.uri.split('#')[0];
                return baseUri + '#' + encodeURIComponent(REMARK_TAG);
            });

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
