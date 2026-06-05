from types import ModuleType
from unittest.mock import patch

from tradingagents.llm_clients.request_options import normalize_request_options


def test_moonshot_kimi_k2_temperature_is_forced_to_one():
    options = normalize_request_options(
        "moonshot",
        "kimi-k2.6",
        {"max_tokens": 200, "temperature": 0.1},
    )

    assert options["temperature"] == 1


def test_moonshot_v1_temperature_is_left_unchanged():
    options = normalize_request_options(
        "moonshot",
        "moonshot-v1-128k",
        {"max_tokens": 200, "temperature": 0.1},
    )

    assert options["temperature"] == 0.1


def test_openai_compatible_client_normalizes_moonshot_kimi_k2_temperature():
    fake_langchain_openai = ModuleType("langchain_openai")

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_langchain_openai.ChatOpenAI = FakeChatOpenAI

    with patch.dict("sys.modules", {"langchain_openai": fake_langchain_openai}):
        from tradingagents.llm_clients.openai_client import OpenAIClient

        llm = OpenAIClient("kimi-k2.6", provider="moonshot", temperature=0.1).get_llm()

    assert llm.kwargs["temperature"] == 1
