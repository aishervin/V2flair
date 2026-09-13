import express from 'express';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

const REMARK_PREFIX = "®️SHΞN™ᴢᴇʀᴏ";
const REMARK_SUFFIX = "T.me/Shervini";
const MAX_OUTPUT = 2000;

const GEOIP_CACHE = new Map();
const PRIORITY_TESTED_SOURCE = "https://raw.githubusercontent.com/aishervin/V2flair/main/clean_sub.txt";

const SOURCES = [
  // 1. High-priority tested source from Python pipeline
  PRIORITY_TESTED_SOURCE,

  // 2. Active Multi-protocol Sources (VLESS, VMess, Hysteria2)
  "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/mix",
  "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria",
  "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hy2",
  "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vmess",
  "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
  "https://raw.githubusercontent.com/MrPooyaCou/V2root/main/HY2.txt",
  "https://raw.githubusercontent.com/MrPooyaCou/V2root/main/VMess.txt",
  "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/hysteria2.txt",
  "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
  "https://raw.githubusercontent.com/freefq/free/master/v2",
  "https://raw.githubusercontent.com/vpei/Free-Node-Merge/main/node.txt",
  "https://raw.githubusercontent.com/mahsanet/v2ray-configs/main/all_configs.txt",

  // 3. Additional curated active repos
  "https://raw.githubusercontent.com/aishervin/subfine/refs/heads/main/sub.txt",
  "https://raw.githubusercontent.com/aishervin/v2ray/refs/heads/main/Sub.json",
  "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/refs/heads/main/all/configs.txt",
  "https://raw.githubusercontent.com/iboxz/free-v2ray-collector/main/main/vless.txt",
  "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
  "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
  "https://raw.githubusercontent.com/F0rc3Run/F0rc3Run/refs/heads/main/splitted-by-protocol/vless.txt",
  "https://raw.githubusercontent.com/barry-far/V2ray-config/refs/heads/main/Sub1.txt",
  "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/Sub2.txt",
  "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
  "https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/refs/heads/main/subscriptions/all.txt",
  "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/refs/heads/main/sub.txt",
  "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/vless.txt",
  "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/subscriptions/reality.txt",
  "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt",
  "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
  "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vless_iran.txt"
];

function countryCodeToFlagEmoji(countryCode) {
  if (!countryCode || countryCode.length !== 2) return "🌐";
  const code = countryCode.toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return "🌐";
  const codePoints = code.split('').map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

function extractFlagFromText(text) {
  if (!text) return "";
  const flagMatch = text.match(/[\uD83C][\uDDE6-\uDDFF][\uD83C][\uDDE6-\uDDFF]/);
  if (flagMatch) return flagMatch[0];
  const ccMatch = text.match(/\b(US|DE|GB|UK|FR|NL|FI|SE|SG|JP|KR|CA|TR|IR|RU|AE|CH|PL|IT|ES)\b/i);
  if (ccMatch) {
    let code = ccMatch[1].toUpperCase();
    if (code === 'UK') code = 'GB';
    return countryCodeToFlagEmoji(code);
  }
  return "";
}

function makeRemark(flag) {
  const f = flag || "🌐";
  return `${REMARK_PREFIX}${f}${REMARK_SUFFIX}`;
}

function safeAtobUnicode(str) {
  try {
    let s = str.trim().replace(/-/g, "+").replace(/_/g, "/");
    const pad = s.length % 4;
    if (pad) s += "=".repeat(4 - pad);
    return Buffer.from(s, 'base64').toString('utf-8');
  } catch (e) {
    return str;
  }
}

function safeBtoaUnicode(str) {
  try {
    return Buffer.from(str, 'utf-8').toString('base64');
  } catch (e) {
    return Buffer.from(str).toString('base64');
  }
}

async function lookupGeoIP(host) {
  if (!host) return "";
  if (GEOIP_CACHE.has(host)) return GEOIP_CACHE.get(host);

  try {
    const res = await fetch(`https://api.ip.sb/geoip/${encodeURIComponent(host)}`, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
      signal: AbortSignal.timeout(2500)
    });
    if (res.ok) {
      const data = await res.json();
      const code = data.country_code || "";
      if (code) {
        const flag = countryCodeToFlagEmoji(code);
        GEOIP_CACHE.set(host, flag);
        return flag;
      }
    }
  } catch (e) {}

  return "";
}

async function handleSubscription(req, res) {
  let combinedData = "";
  let priorityConfigs = [];

  // If local clean_sub.txt exists and has content, read it as local high-priority
  const localCleanPath = path.join(__dirname, 'clean_sub.txt');
  if (fs.existsSync(localCleanPath)) {
    try {
      const localContent = fs.readFileSync(localCleanPath, 'utf-8');
      if (localContent && localContent.length > 20) {
        priorityConfigs.push(localContent);
      }
    } catch (e) {}
  }

  const fetchPromises = SOURCES.map(async (srcUrl) => {
    try {
      const isPriority = (srcUrl === PRIORITY_TESTED_SOURCE);
      const response = await fetch(srcUrl, {
        headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
        signal: AbortSignal.timeout(6000)
      });
      if (response.ok) {
        let text = await response.text();
        if (isPriority) {
          priorityConfigs.push(text);
        } else {
          combinedData += '\n' + text;
        }
      }
    } catch (err) {}
  });

  await Promise.all(fetchPromises);

  let allContent = priorityConfigs.join('\n') + '\n' + combinedData;

  const lines = allContent.split(/\r?\n/);
  for (let line of lines) {
    let s = line.trim();
    if (s.length > 50 && !s.includes('://') && /^[A-Za-z0-9+/=_-]+$/.test(s)) {
      try {
        const decoded = safeAtobUnicode(s);
        if (decoded.includes('://')) allContent += '\n' + decoded;
      } catch (e) {}
    }
  }

  const regex = /(vless|vmess|hysteria2|hy2):\/\/[^\s"'<>]+/gim;
  const matches = allContent.match(regex) || [];
  const uniqueConfigsMap = new Map();

  let priorityIndex = 0;

  for (let uri of matches) {
    try {
      let proto = '';
      let host = '';
      let port = 443;
      let net = 'tcp';
      let security = 'tls';
      let rawRemark = '';
      let vmessData = null;
      let isTestedPriority = false;

      // Check if from priority tested list
      for (const pConf of priorityConfigs) {
        if (pConf.includes(uri)) {
          isTestedPriority = true;
          break;
        }
      }

      if (uri.startsWith('vmess://')) {
        proto = 'vmess';
        const decoded = safeAtobUnicode(uri.slice(8));
        if (!decoded) continue;
        vmessData = JSON.parse(decoded);
        host = vmessData.add || '';
        port = parseInt(vmessData.port) || 443;
        net = (vmessData.net || 'ws').toLowerCase();
        security = (vmessData.tls || 'none').toLowerCase();
        rawRemark = vmessData.ps || '';
      } else {
        const hashIdx = uri.indexOf('#');
        const base = hashIdx !== -1 ? uri.substring(0, hashIdx) : uri;
        rawRemark = hashIdx !== -1 ? decodeURIComponent(uri.substring(hashIdx + 1)) : '';

        const pMatch = base.match(/^([a-zA-Z0-9]+):\/\//);
        if (!pMatch) continue;
        proto = pMatch[1].toLowerCase();

        const fakeUrlStr = 'http://' + base.slice(pMatch[0].length);
        const fakeUrl = new URL(fakeUrlStr);

        host = fakeUrl.hostname;
        port = parseInt(fakeUrl.port) || 443;
        const params = new URLSearchParams(fakeUrl.search);
        net = (params.get('type') || params.get('mode') || (proto.includes('hy') ? 'udp' : 'tcp')).toLowerCase();
        security = (params.get('security') || (proto.includes('hy') ? 'tls' : '')).toLowerCase();
      }

      if (!host) continue;

      const key = `${proto}|${host}|${port}|${net}`;

      let score = 50;
      if (isTestedPriority) {
        score += 10000 - priorityIndex;
        priorityIndex++;
      }

      if (proto === 'hysteria2' || proto === 'hy2') score += 55;
      if (security === 'reality') score += 40;
      else if (security === 'tls' || security === 'xtls') score += 15;

      if (['grpc', 'xhttp', 'ws'].includes(net)) score += 20;
      if ([443, 8443, 2053, 2083].includes(port)) score += 5;

      const existing = uniqueConfigsMap.get(key);
      if (!existing || score > existing.score) {
        uniqueConfigsMap.set(key, {
          proto,
          uri: uri.trim(),
          host,
          rawRemark,
          vmessData,
          score,
          isTestedPriority
        });
      }
    } catch (e) {}
  }

  const sortedList = Array.from(uniqueConfigsMap.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_OUTPUT);

  // Resolve flags for top 30
  const topGeo = sortedList.slice(0, 30);
  await Promise.all(topGeo.map(async (item) => {
    const existingFlag = extractFlagFromText(item.rawRemark);
    if (existingFlag) {
      item.flag = existingFlag;
    } else {
      item.flag = await lookupGeoIP(item.host);
    }
  }));

  const finalConfigs = sortedList.map(item => {
    const flag = item.flag || extractFlagFromText(item.rawRemark) || "🌐";
    const remark = makeRemark(flag);

    if (item.proto === 'vmess' && item.vmessData) {
      const cloned = { ...item.vmessData, ps: remark };
      return 'vmess://' + safeBtoaUnicode(JSON.stringify(cloned));
    } else {
      const baseUri = item.uri.split('#')[0];
      return baseUri + '#' + encodeURIComponent(remark);
    }
  });

  const finalPayload = finalConfigs.join('\n');
  const b64Payload = safeBtoaUnicode(finalPayload);

  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Profile-Update-Interval", "1");
  res.setHeader("Subscription-Userinfo", "upload=829900; download=65886; total=19737418240000; expire=0");
  res.status(200).send(b64Payload);
}

// Dedicated subscription routes
app.get('/sub', handleSubscription);
app.get('/api/sub', handleSubscription);

// Root route handler
app.get('/', (req, res, next) => {
  const accept = req.headers['accept'] || '';
  const userAgent = (req.headers['user-agent'] || '').toLowerCase();
  const isBrowser = accept.includes('text/html') && 
                    !userAgent.includes('v2ray') && 
                    !userAgent.includes('sing-box') &&
                    !userAgent.includes('nekobox') &&
                    !userAgent.includes('clash') &&
                    !userAgent.includes('vless') &&
                    !userAgent.includes('vmess') &&
                    !userAgent.includes('hysteria');

  if (!isBrowser || req.query.sub !== undefined) {
    return handleSubscription(req, res);
  }
  next();
});

// Serve static files
app.use(express.static(__dirname));

// Fallback to index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on http://0.0.0.0:${PORT}`);
});
