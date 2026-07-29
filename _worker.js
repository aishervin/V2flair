/**
 * Exclusive ☬SHΞN™ made
 * Vless Advanced Filter, Aggregator & Scorer
 * Scoring based on real-world tested configs
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

        // فقط کانفیگ‌های vless استخراج می‌شوند
        const regex = /vless:\/\/[^\s"'<>]+/gim;
        const matches = combinedData.match(regex) || [];
        const uniqueConfigsMap = new Map();

        for (let uri of matches) {
            try {
                // استخراج پارامترها با یک URL جعلی
                const uriWithoutProtocol = uri.replace(/^vless:\/\//i, '');
                const fakeUrlStr = 'http://' + uriWithoutProtocol;
                const fakeUrl = new URL(fakeUrlStr);

                const hostname = fakeUrl.hostname;
                const port = parseInt(fakeUrl.port) || 443; // پورت پیش‌فرض ۴۴۳
                const params = new URLSearchParams(fakeUrl.search);

                let net = (params.get('type') || 'tcp').toLowerCase();
                let security = (params.get('security') || '').toLowerCase();
                let flow = (params.get('flow') || '').toLowerCase();

                // فقط شبکه‌های مجاز
                const allowedNets = ['ws', 'grpc', 'tcp', 'xhttp'];
                const allowedSec = ['tls', 'reality', 'xtls', 'none', ''];

                if (!allowedNets.includes(net) && !allowedSec.includes(security)) {
                    continue;
                }
                if (!security) security = 'none';

                // کلید یکتاسازی: host:port:net
                const key = `${hostname}|${port}|${net}`;

                // ========= امتیازدهی جدید =========
                let score = 40; // پایه

                // امنیت
                if (security === 'reality') {
                    score += 50;
                } else if (security === 'tls' || security === 'xtls') {
                    score += 20;
                }

                // نوع شبکه
                if (net === 'grpc') {
                    score += 25;
                } else if (net === 'xhttp') {
                    score += 25;
                } else if (net === 'ws') {
                    score += 20;
                } else if (net === 'tcp') {
                    // فقط در صورت وجود xtls-rprx-vision
                    if (flow === 'xtls-rprx-vision') {
                        score += 25;
                    }
                    // tcp بدون vision هیچ امتیاز اضافی نمی‌گیرد
                }

                // پورت‌های طلایی
                if ([443, 8443, 2096, 2087, 2053].includes(port)) {
                    score += 10;
                }

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
