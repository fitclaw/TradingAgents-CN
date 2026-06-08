"""Unit tests for the standalone Grok/X data source adapter.

Uses unittest (no pytest dependency) and fully mocks HTTP, so it never calls
the real xAI API. The adapter is intentionally NOT wired into the analysis chain.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tradingagents.dataflows.providers.grok.grok_x_client import (
    GrokXClient,
    GrokXError,
    GrokXSignal,
)

# A valid-looking dummy key: >10 chars, not a your_*/*_here placeholder.
VALID_KEY = "xai-test-key-0123456789"
PLACEHOLDER_KEY = "your_xai_api_key_here"  # the .env.example default


def _api_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


SAMPLE = _api_response(
    '{"signals":['
    '{"title":"Apple beats","summary":"AAPL up on earnings","category":"news",'
    '"sentiment":"positive","url":"https://x.com/a/1","author":"@trader",'
    '"published_at":"2026-06-05T10:00:00Z"},'
    '{"title":"chatter","summary":"retail bullish","category":"social","sentiment":"weird"}'
    ']}'
)


class GrokXParsingTests(unittest.TestCase):
    def setUp(self):
        self.client = GrokXClient(api_key=VALID_KEY)

    def test_parse_valid_response(self):
        signals = self.client._parse_response(
            SAMPLE, allowed_categories=["news", "social"], limit=20
        )
        self.assertEqual(len(signals), 2)
        self.assertIsInstance(signals[0], GrokXSignal)
        self.assertEqual(signals[0].category, "news")
        self.assertEqual(signals[0].sentiment, "positive")
        self.assertEqual(signals[0].source, "grok_x")
        # invalid sentiment ("weird") normalized to None
        self.assertIsNone(signals[1].sentiment)

    def test_parse_filters_disallowed_category(self):
        signals = self.client._parse_response(
            SAMPLE, allowed_categories=["news"], limit=20
        )
        self.assertEqual([s.category for s in signals], ["news"])

    def test_parse_respects_limit(self):
        signals = self.client._parse_response(
            SAMPLE, allowed_categories=["news", "social"], limit=1
        )
        self.assertEqual(len(signals), 1)

    def test_parse_strips_code_fences(self):
        raw = _api_response('```json\n{"signals":[]}\n```')
        self.assertEqual(
            self.client._parse_response(raw, allowed_categories=["news"], limit=5), []
        )

    def test_parse_invalid_json_raises(self):
        with self.assertRaises(GrokXError):
            self.client._parse_response(
                _api_response("not json"), allowed_categories=["news"], limit=5
            )

    def test_parse_missing_content_raises(self):
        with self.assertRaises(GrokXError):
            self.client._parse_response(
                {"choices": []}, allowed_categories=["news"], limit=5
            )


class GrokXConfigTests(unittest.TestCase):
    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"XAI_API_KEY": VALID_KEY}, clear=False):
            self.assertTrue(GrokXClient().is_configured())

    def test_missing_key_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(GrokXClient().is_configured())

    def test_placeholder_key_not_configured(self):
        # .env.example default must NOT count as configured
        self.assertFalse(GrokXClient(api_key=PLACEHOLDER_KEY).is_configured())

    def test_short_key_not_configured(self):
        self.assertFalse(GrokXClient(api_key="k").is_configured())

    def test_whitespace_key_not_configured(self):
        self.assertFalse(GrokXClient(api_key="   ").is_configured())

    def test_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GrokXClient(api_key=VALID_KEY)
            self.assertEqual(client.base_url, "https://api.x.ai/v1")
            self.assertEqual(client.model, "grok-2-latest")

    def test_base_url_and_model_override_via_env(self):
        with patch.dict(
            "os.environ",
            {"XAI_BASE_URL": "https://proxy/v1/", "XAI_GROK_MODEL": "grok-3"},
            clear=True,
        ):
            client = GrokXClient(api_key=VALID_KEY)
            self.assertEqual(client.base_url, "https://proxy/v1")  # trailing slash stripped
            self.assertEqual(client.model, "grok-3")


class GrokXPayloadTests(unittest.TestCase):
    def setUp(self):
        self.client = GrokXClient(api_key=VALID_KEY)

    def test_payload_includes_live_x_search(self):
        msgs = self.client._build_messages("AAPL", ["news"], 24, 10)
        payload = self.client._build_payload(
            msgs, 24, 10, now=datetime(2026, 6, 5, tzinfo=timezone.utc)
        )
        self.assertEqual(payload["model"], "grok-2-latest")
        self.assertEqual(payload["search_parameters"]["mode"], "on")
        self.assertEqual(payload["search_parameters"]["sources"], [{"type": "x"}])
        self.assertEqual(payload["search_parameters"]["from_date"], "2026-06-04")
        self.assertEqual(payload["search_parameters"]["to_date"], "2026-06-05")
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_unsupported_category_raises(self):
        with self.assertRaises(GrokXError):
            self.client.fetch_x_signals("AAPL", categories=["prices"])

    def test_empty_query_raises(self):
        with self.assertRaises(GrokXError):
            self.client.fetch_x_signals("   ")

    def test_missing_key_fetch_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GrokXClient()
            with self.assertRaises(GrokXError):
                client.fetch_x_signals("AAPL")

    def test_placeholder_key_fetch_raises_before_http(self):
        # placeholder must fail locally, NOT by sending the placeholder to xAI
        client = GrokXClient(api_key=PLACEHOLDER_KEY)
        with patch.object(GrokXClient, "_call_api") as mocked:
            with self.assertRaises(GrokXError):
                client.fetch_x_signals("AAPL")
        mocked.assert_not_called()


class GrokXFetchTests(unittest.TestCase):
    def test_fetch_uses_call_api_and_returns_dicts(self):
        client = GrokXClient(api_key=VALID_KEY)
        with patch.object(GrokXClient, "_call_api", return_value=SAMPLE) as mocked:
            out = client.fetch_x_signals("AAPL", categories=["news", "social"], limit=20)
        mocked.assert_called_once()
        self.assertEqual(len(out), 2)
        self.assertTrue(all(isinstance(x, dict) for x in out))
        self.assertEqual(out[0]["source"], "grok_x")

    def test_call_api_isolated_via_injected_session(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = SAMPLE
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.post.return_value = fake_resp

        client = GrokXClient(api_key=VALID_KEY, session=fake_session)
        out = client.fetch_x_signals("AAPL", categories=["news"], limit=5)

        fake_session.post.assert_called_once()
        _, kwargs = fake_session.post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {VALID_KEY}")
        self.assertEqual(out[0]["category"], "news")

    def test_call_api_http_error_wrapped(self):
        fake_session = MagicMock()
        fake_session.post.side_effect = RuntimeError("boom")
        client = GrokXClient(api_key=VALID_KEY, session=fake_session)
        with self.assertRaises(GrokXError):
            client.fetch_x_signals("AAPL", categories=["news"])


if __name__ == "__main__":
    unittest.main()
