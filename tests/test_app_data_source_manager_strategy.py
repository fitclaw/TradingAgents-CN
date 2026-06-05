import sys
from types import ModuleType


if "pandas" not in sys.modules:
    fake_pandas = ModuleType("pandas")
    fake_pandas.DataFrame = object
    sys.modules["pandas"] = fake_pandas

from app.services.data_sources.manager import DataSourceManager


class FakeAdapter:
    def __init__(self, name: str):
        self.name = name
        self.priority = 0

    def is_available(self) -> bool:
        return True


def _manager(strategy: str) -> DataSourceManager:
    manager = DataSourceManager.__new__(DataSourceManager)
    manager.strategy = strategy
    manager.adapters = [
        FakeAdapter("tushare"),
        FakeAdapter("akshare"),
        FakeAdapter("baostock"),
    ]
    return manager


def _ordered_names(manager: DataSourceManager, capability: str, preferred_sources=None):
    return [
        adapter.name
        for adapter in manager._get_ordered_available_adapters(capability, preferred_sources)
    ]


def test_free_first_kline_excludes_tushare_premium_source():
    assert _ordered_names(_manager("free_first"), "kline") == ["akshare", "baostock"]


def test_premium_enhanced_kline_can_include_tushare():
    assert _ordered_names(_manager("premium_enhanced"), "kline") == [
        "akshare",
        "baostock",
        "tushare",
    ]


def test_preferred_sources_reorder_only_allowed_strategy_sources():
    manager = _manager("free_first")

    assert _ordered_names(manager, "kline", ["baostock", "akshare"]) == [
        "baostock",
        "akshare",
    ]
    assert _ordered_names(manager, "kline", ["tushare", "akshare"]) == [
        "akshare",
        "baostock",
    ]


def test_quality_first_news_allows_free_adapter_not_premium_adapter():
    assert _ordered_names(_manager("quality_first"), "news") == ["akshare"]


def test_invalid_strategy_resolves_to_free_first():
    manager = DataSourceManager.__new__(DataSourceManager)

    assert manager._resolve_strategy("unknown") == "free_first"
