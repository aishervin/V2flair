// ==================== تابع کمکی برای دریافت کانفیگ از خودمان ====================
async function fetchOwnConfigs() {
    // با اضافه کردن ?sub=1، Worker اصلی را مجبور می‌کنیم که همان خروجی Base64 را برگرداند
    const response = await fetch('https://subshen.pages.dev/?sub=1', {
        headers: {
            'User-Agent': 'v2ray' // شبیه‌سازی یک کلاینت برای دریافت محتوای خام
        }
    });
    if (!response.ok) {
        throw new Error(`Failed to fetch configs: ${response.status}`);
    }
    const base64Text = await response.text();
    // دیکد کردن Base64 به متن اصلی
    const decoded = atob(base64Text);
    return decoded;
}

// ==================== تابع تولید کانفیگ‌های گسترش‌یافته ====================
async function generateExpandedConfigs() {
    // ۱. دریافت کانفیگ‌های تمیز از خودمان
    const configsText = await fetchOwnConfigs();
    const matches = configsText.match(/vless:\/\/[^\s"'<>]+/gim) || [];

    // ۲. تشخیص گروه‌های تکراری (همان منطق قبلی)
    function parseVless(uri) {
        try {
            const u = new URL(uri);
            const host = u.hostname;
            const port = parseInt(u.port) || 443;
            const uuid = u.username;
            const params = new URLSearchParams(u.search);
            return { uuid, host, port, params };
        } catch { return null; }
    }

    function getGroupKey(parsed) {
        const { uuid, host, params } = parsed;
        const p = Object.fromEntries(params.entries());
        // حذف پارامترهای متغیر
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
        if (items.length >= 2) {
            duplicateGroups.push(items);
        }
    }

    // ۳. تولید رنج /24 برای هر گروه
    function expandTo24(groupItems) {
        const base = groupItems[0];
        const hostParts = base.host.split('.');
        if (hostParts.length !== 4) return [];
        const prefix = hostParts.slice(0, 3).join('.');
        const newConfigs = [];
        for (let i = 0; i <= 255; i++) {
            const newHost = `${prefix}.${i}`;
            const params = new URLSearchParams(base.params);
            const search = params.toString();
            const uri = `vless://${base.uuid}@${newHost}:${base.port}${search ? '?'+search : ''}#${encodeURIComponent('☬SH℮N™ /24 '+prefix+'.'+i)}`;
            newConfigs.push(uri);
        }
        return newConfigs;
    }

    let allExpanded = [];
    // فقط ۵ گروه اول را پردازش می‌کنیم (برای جلوگیری از timeout)
    const limitedGroups = duplicateGroups.slice(0, 5);
    for (const group of limitedGroups) {
        const expanded = expandTo24(group);
        allExpanded = allExpanded.concat(expanded);
    }

    if (allExpanded.length === 0) {
        return '# No duplicate groups found to expand.';
    }
    return allExpanded.join('\n');
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
        // ... (همان کد قبلی شما برای تولید ساب‌لینک) ...
        // برای اختصار، اینجا فقط یک نمونه از کد قبلی را می‌گذارم.
        // شما باید کد کامل قبلی خود را اینجا قرار دهید.
        // ...
        // در غیر این صورت، یک پاسخ پیش‌فرض برمی‌گردانیم.
        return new Response('☬SHΞN™ Subnet Detector - Use /extender for expanded configs', {
            status: 200,
            headers: { 'Content-Type': 'text/html' }
        });
    }
};
