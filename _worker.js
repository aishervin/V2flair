/**
 * Exclusive ☬SHΞN™ made
 * Vless & Vmess Advanced Filter, Aggregator & Scorer
 * Updated: now includes full vmess support
 */

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        const accept = request.headers.get('Accept') || '';
        const userAgent = (request.headers.get('User-Agent') || '').toLowerCase();

        // تشخیص مرورگر
        const isBrowser = accept.includes('text/html') &&
                          !userAgent.includes('v2ray') &&
                          !userAgent.includes('sing-box') &&
                          !userAgent.includes('nekobox') &&
                          !userAgent.includes('clash') &&
                          !userAgent.includes('vless') &&
                          !userAgent.includes('vmess');

        if (isBrowser && !url.searchParams.has('sub')) {
            return env.ASSETS.fetch(request);
        }

        // ==========================================
        // منابع کانفیگ
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

        const REMARK_TAG = "☬SHΞN™  Ai core worker";
        const MAX_OUTPUT = 3500;

        // رمزگشایی بیس ۶۴ با پشتیبانی از یونیکد
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

        // دریافت تمام منابع
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

        // رمزگشایی خطوط بیس۶۴ طولانی (اشتراک کامل)
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

        // جستجوی هر دو پروتکل
        const regex = /(vless|vmess):\/\/[^\s"'<>]+/gim;
        const matches = combinedData.match(regex) || [];
        const uniqueConfigsMap = new Map();

        for (let rawUri of matches) {
            let uri = rawUri.trim();
            const protocol = uri.match(/^(vless|vmess)/i)[0].toLowerCase();

            // ========== تبدیل vmess base64 به فرمت جدید ==========
            if (protocol === 'vmess') {
                const rest = uri.slice(8); // بعد از "vmess://"
                // اگر rest حاوی '@' یا '?' باشد، احتمالاً فرمت جدید است
                const isNewFormat = rest.includes('@') || rest.includes('?');
                if (!isNewFormat) {
                    // احتمالاً base64 – رمزگشایی و ساخت لینک جدید
                    try {
                        const jsonStr = safeAtobUnicode(rest);
                        const json = JSON.parse(jsonStr);
                        if (!json.add || !json.port || !json.id) continue;

                        const params = new URLSearchParams();
                        params.set('encryption', 'auto');
                        if (json.tls === 'tls') params.set('security', 'tls');
                        if (json.net) params.set('type', json.net);
                        if (json.host) params.set('host', json.host);
                        if (json.path) params.set('path', json.path);
                        if (json.sni) params.set('sni', json.sni);

                        const newUri = `vmess://${json.id}@${json.add}:${json.port}?${params.toString()}`;
                        // remark را به انتها اضافه می‌کنیم (در انتها توسط کد جایگزین می‌شود)
                        uri = newUri + '#' + (json.ps ? encodeURIComponent(json.ps) : 'vmess');
                    } catch (e) {
                        continue; // رمزگشایی یا JSON نامعتبر
                    }
                }
            }

            // ========== پردازش یکسان برای vless و vmess ==========
            try {
                // ساخت یک URL جعلی برای استخراج پارامترها
                const uriWithoutProtocol = uri.replace(/^[a-z]+:\/\//i, '');
                const fakeUrlStr = 'http://' + uriWithoutProtocol;
                const fakeUrl = new URL(fakeUrlStr);

                const hostname = fakeUrl.hostname;
                const port = parseInt(fakeUrl.port) || (protocol === 'vmess' ? 80 : 443); // پورت پیش‌فرض بر اساس پروتکل
                const params = new URLSearchParams(fakeUrl.search);

                let net = (params.get('type') || params.get('mode') || 'tcp').toLowerCase();
                let security = (params.get('security') || '').toLowerCase();

                // فیلتر شبکه و امنیت (با پشتیبانی از vmess بدون TLS)
                const allowedNets = ['ws', 'grpc', 'tcp', 'http', 'xhttp'];
                const allowedSec = ['tls', 'reality', 'tcp', 'xtls', 'none'];
                if (!security) security = 'none'; // vmess بدون TLS را مجاز می‌کنیم

                if (!allowedNets.includes(net) && !allowedSec.includes(security)) {
                    continue;
                }

                // کلید یکتاسازی
                const key = `${hostname}|${port}|${net}`;

                // امتیازدهی
                let score = 50;
                if (security === 'reality') score += 30;
                else if (security === 'tls' || security === 'xtls') score += 20;
                
                if (['grpc', 'xhttp', 'ws'].includes(net)) score += 15;
                if ([443, 8443, 2053, 2083, 80, 8080].includes(port)) score += 15;

                // ذخیره بهترین کانفیگ بر اساس کلید
                const existing = uniqueConfigsMap.get(key);
                if (!existing || score > existing.score) {
                    uniqueConfigsMap.set(key, { uri: uri.split('#')[0], score: score });
                }
            } catch (e) {}
        }

        // مرتب‌سازی و محدودیت خروجی
        const sortedConfigs = Array.from(uniqueConfigsMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, MAX_OUTPUT)
            .map(item => {
                return item.uri + '#' + encodeURIComponent(REMARK_TAG);
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
