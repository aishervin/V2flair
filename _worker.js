/**
 * Exclusive ☬SHΞN™ made
 * Vless Advanced Filter, Aggregator & Scorer
 */

export default {
    async fetch(request, env, ctx) {
        // ۱. لیست سورس‌های استخراج شده از اسپلیتر
        const SOURCES = [
            "https://raw.githubusercontent.com/shervinofpersia/Config/refs/heads/main/ProxyNg.json",
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
            "https://raw.githubusercontent.com/Pawdroid/Free-servers/refs/heads/main/sub",
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

        const REMARK_TAG = "☬SHΞN™  Telegramer.page.dev";
        const MAX_OUTPUT = 3000;

        // تابع دیکد Base64 (برداشته شده از اسپلیتر شما)
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

        // ۲. دریافت موازی تمام سورس‌ها (سرعت بالا)
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

        // استخراج و دیکد لینک‌های پنهان تو Base64
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

        // ۳. Regex اختصاصی فقط برای VLESS
        const regex = /(vless):\/\/[^\s"'<>]+/gim;
        const matches = combinedData.match(regex) || [];
        const uniqueConfigsMap = new Map();

        // ۴. تحلیل، فیلتر و امتیازدهی
        for (let uri of matches) {
            try {
                // پارس کردن لینک
                const lowUri = uri.toLowerCase();
                const fakeUrlStr = 'http://' + lowUri.slice(8); // bypass vless://
                const fakeUrl = new URL(fakeUrlStr);
                
                const port = parseInt(fakeUrl.port) || 443;
                const params = new URLSearchParams(fakeUrl.search);
                
                const net = (params.get('type') || params.get('mode') || 'tcp').toLowerCase();
                const security = (params.get('security') || '').toLowerCase();

                // شرط فیلتر شما: Vless و یکی از شبکه‌های ws, grpc, http, xhttp یا سکیوریتی tls, reality
                const allowedNets = ['ws', 'grpc', 'http', 'httpupgrade', 'splithttp', 'xhttp'];
                const allowedSec = ['tls', 'reality', 'xtls'];

                if (!allowedNets.includes(net) && !allowedSec.includes(security)) {
                    continue; // رد کردن کانفیگ‌هایی که تو لیست شما نیستند
                }

                // ساخت کلید یکتا برای حذف تکراری‌ها (فقط یک کانفیگ برای هر آی‌پی و پورت)
                const key = `${fakeUrl.hostname}|${port}|${net}`;

                // سیستم امتیازدهی (Scoring) شما برای شبیه‌سازی تاخیر کمتر
                let score = 50;
                if (security === 'reality') score += 30;
                else if (security === 'tls' || security === 'xtls') score += 20;
                
                if (['grpc', 'xhttp', 'ws'].includes(net)) score += 15;
                if ([443, 8443, 2053, 2083].includes(port)) score += 15; // پورت‌های استاندارد کلودفلر

                const existing = uniqueConfigsMap.get(key);
                if (!existing || score > existing.score) {
                    uniqueConfigsMap.set(key, { uri: uri.trim(), score: score });
                }
            } catch (e) {
                // کانفیگ نامعتبر نادیده گرفته می‌شود
            }
        }

        // ۵. مرتب‌سازی بر اساس بالاترین امتیاز (کمترین تاخیر) و ریمارک زدن
        const sortedConfigs = Array.from(uniqueConfigsMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, MAX_OUTPUT)
            .map(item => {
                const baseUri = item.uri.split('#')[0];
                return baseUri + '#' + encodeURIComponent(REMARK_TAG);
            });

        // ۶. خروجی نهایی: کد کردن به فرمت استاندارد Base64 برای کلاینت‌ها (جلوگیری از خطا)
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
