"""Unit tests for the pure pipeline pieces (stdlib only).

Run:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import config  # noqa: E402
from parse import (  # noqa: E402
    dedupe,
    extract_uris,
    flag_for,
    final_remark,
    parse_uri,
    publish_uri,
)
from rank import score_node, select  # noqa: E402
from verify import verify  # noqa: E402

UUID = "dc1e9f00-c064-4870-9bfc-463db50257d7"
REALITY = (
    f"vless://{UUID}@example.com:443?encryption=none&security=reality"
    "&sni=cdn.example.com&fp=chrome&pbk=abcDEF123&sid=1a2b&type=tcp"
    "&flow=xtls-rprx-vision#%F0%9F%87%A9%F0%9F%87%AA%20DE"
)


class ParseTests(unittest.TestCase):
    def test_reality(self) -> None:
        node = parse_uri(REALITY)
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.uid, UUID)
        self.assertEqual(node.security, "reality")
        self.assertEqual(node.flow, "xtls-rprx-vision")
        self.assertEqual(node.sni, "cdn.example.com")
        self.assertEqual(node.pbk, "abcDEF123")
        self.assertEqual(node.flag, "\U0001F1E9\U0001F1EA")

    def test_ws_defaults_and_normalisation(self) -> None:
        uri = f"vless://{UUID}@1.1.1.1:8443?type=ws&path=%2Fabc&host=cdn.x.com&security=tls&sni=x.com"
        node = parse_uri(uri)
        assert node is not None
        self.assertEqual(node.net, "ws")
        self.assertEqual(node.path, "/abc")
        self.assertEqual(node.host_header, "cdn.x.com")
        self.assertIn("security=tls", node.uri)
        self.assertIn("type=ws", node.uri)

    def test_rejects_junk(self) -> None:
        cases = [
            f"vless://{UUID}@127.0.0.1:443?security=tls&sni=x.com",
            f"vless://{UUID}@10.0.0.5:443?security=tls&sni=x.com",
            f"vless://{UUID}@localhost:443?security=tls&sni=x.com",
            f"vless://not-a-uuid@example.com:443?security=tls&sni=x.com",
            f"vless://{UUID}@example.com:0?security=tls&sni=x.com",
            f"vless://{UUID}@example.com:443?security=reality&sni=x.com",  # no pbk
            f"vless://{UUID}@example.com:443?security=quic",
            f"vmess://{UUID}@example.com:443",
            "garbage",
        ]
        for uri in cases:
            with self.subTest(uri=uri):
                self.assertIsNone(parse_uri(uri))

    def test_dedupe_semantic(self) -> None:
        a = parse_uri(f"vless://{UUID}@example.com:443?security=tls&sni=x.com&type=ws&path=%2F")
        b = parse_uri(f"vless://{UUID}@example.com:443?path=%2F&type=ws&sni=x.com&security=tls")
        assert a and b
        self.assertEqual(a.key, b.key)
        self.assertEqual(len(dedupe([a, b])), 1)

    def test_remark(self) -> None:
        node = parse_uri(REALITY)
        assert node is not None
        node.flag = flag_for("TR")
        remark = final_remark(node)
        self.assertEqual(remark, "\U0001F1F9\U0001F1F7" + config.BRAND)
        self.assertIn("#%F0%9F%87%B9%F0%9F%87%B7", publish_uri(node))

    def test_base64_payload(self) -> None:
        payload = base64.b64encode((REALITY + "\n").encode()).decode()
        uris = extract_uris(payload)
        self.assertEqual(len(uris), 1)
        self.assertTrue(uris[0].startswith("vless://"))

    def test_metadata_lines_ignored(self) -> None:
        text = "#profile-title: x\n//profile-update-interval: 1\n" + REALITY
        self.assertEqual(len(extract_uris(text)), 1)


class RankTests(unittest.TestCase):
    def test_better_node_wins(self) -> None:
        fast = parse_uri(REALITY)
        slow = parse_uri(REALITY.replace("example.com", "example.org").replace("1a2b", "9z8y"))
        assert fast and slow
        fast.latency_ms, fast.speed_kbps, fast.ok, fast.fail = 120, 6000, 2, 0
        slow.latency_ms, slow.speed_kbps, slow.ok, slow.fail = 900, 700, 1, 1
        score_node(fast)
        score_node(slow)
        result = select([slow, fast], limit=10)
        self.assertEqual(result[0].host, "example.com")


class VerifyTests(unittest.TestCase):
    def _write(self, text: str) -> str:
        tmp = tempfile.mkdtemp()
        Path(tmp, "sub.txt").write_text(text, encoding="utf-8")
        Path(tmp, "sub.b64").write_text(
            base64.b64encode(text.encode()).decode() + "\n", encoding="ascii"
        )
        return tmp

    def test_clean_subscription(self) -> None:
        node = parse_uri(REALITY)
        assert node is not None
        node.flag = "\U0001F1F9\U0001F1F7"
        out = self._write(publish_uri(node) + "\n")
        self.assertEqual(verify(out, min_nodes=1), [])

    def test_duplicate_detected(self) -> None:
        node = parse_uri(REALITY)
        assert node is not None
        node.flag = "\U0001F1F9\U0001F1F7"
        line = publish_uri(node) + "\n"
        out = self._write(line + line)
        self.assertTrue(any("duplicate" in e for e in verify(out, min_nodes=1)))

    def test_bad_remark_detected(self) -> None:
        node = parse_uri(REALITY)
        assert node is not None
        node.flag = "\U0001F1F9\U0001F1F7"
        line = publish_uri(node)
        base = line.split("#")[0] + "#wrong\n"
        out = self._write(base)
        self.assertTrue(any("remark" in e for e in verify(out, min_nodes=1)))


if __name__ == "__main__":
    unittest.main()
