from tradingagents.constants import (
    DataSourceCode,
    get_data_source_info,
    list_data_sources_by_access_tier,
    list_data_sources_by_capability,
    list_data_sources_by_market_and_capability,
    list_data_sources_for_strategy,
)


def _codes(infos):
    return {info.code for info in infos}


def test_free_first_registry_marks_core_source_tiers():
    akshare = get_data_source_info(DataSourceCode.AKSHARE)
    baostock = get_data_source_info(DataSourceCode.BAOSTOCK)
    yfinance = get_data_source_info(DataSourceCode.YFINANCE)
    tushare = get_data_source_info(DataSourceCode.TUSHARE)

    assert akshare.access_tier == "free_no_key"
    assert baostock.access_tier == "free_no_key"
    assert yfinance.access_tier == "free_no_key"
    assert tushare.access_tier == "premium_optional"
    assert tushare.default_role == "premium_enhancement"


def test_sec_edgar_is_default_free_us_fundamentals_source():
    sec_edgar = get_data_source_info(DataSourceCode.SEC_EDGAR)

    assert sec_edgar.access_tier == "free_no_key"
    assert sec_edgar.default_role == "default"
    assert "us_stocks" in sec_edgar.supported_markets
    assert "filings" in sec_edgar.capabilities
    assert "fundamentals" in sec_edgar.capabilities

    us_fundamentals = list_data_sources_by_market_and_capability("us_stocks", "fundamentals")
    assert DataSourceCode.SEC_EDGAR in _codes(us_fundamentals)


def test_a_share_stock_list_strategy_uses_free_sources_before_premium_sources():
    free_stock_list = list_data_sources_for_strategy("a_shares", "stock_list", strategy="free_first")
    free_stock_list_codes = _codes(free_stock_list)
    premium_stock_list = list_data_sources_for_strategy("a_shares", "stock_list", strategy="premium_enhanced")
    premium_stock_list_codes = _codes(premium_stock_list)

    assert DataSourceCode.AKSHARE in free_stock_list_codes
    assert DataSourceCode.BAOSTOCK in free_stock_list_codes
    assert DataSourceCode.TUSHARE not in free_stock_list_codes
    assert DataSourceCode.TUSHARE in premium_stock_list_codes


def test_grok_x_is_low_cost_news_social_macro_source_only():
    grok_x = get_data_source_info(DataSourceCode.GROK_X)

    assert grok_x.access_tier == "low_cost"
    assert grok_x.default_role == "optional_enhancement"
    assert "news" in grok_x.capabilities
    assert "social" in grok_x.capabilities
    assert "macro" in grok_x.capabilities
    assert "quotes" not in grok_x.capabilities
    assert "kline" not in grok_x.capabilities
    assert "fundamentals" not in grok_x.capabilities

    news_sources = list_data_sources_by_capability("news")
    assert DataSourceCode.GROK_X in _codes(news_sources)


def test_access_tier_filters_keep_premium_out_of_free_no_key_sources():
    free_no_key_codes = _codes(list_data_sources_by_access_tier("free_no_key"))
    low_cost_codes = _codes(list_data_sources_by_access_tier("low_cost"))
    premium_codes = _codes(list_data_sources_by_access_tier("premium_optional"))

    assert DataSourceCode.AKSHARE in free_no_key_codes
    assert DataSourceCode.YFINANCE in free_no_key_codes
    assert DataSourceCode.SEC_EDGAR in free_no_key_codes
    assert DataSourceCode.GROK_X in low_cost_codes
    assert DataSourceCode.TUSHARE in premium_codes
    assert DataSourceCode.WIND in premium_codes
    assert DataSourceCode.CHOICE in premium_codes

    assert DataSourceCode.TUSHARE not in free_no_key_codes
    assert DataSourceCode.WIND not in free_no_key_codes
    assert DataSourceCode.CHOICE not in free_no_key_codes


def test_free_first_strategy_excludes_low_cost_and_premium_sources():
    us_news = list_data_sources_for_strategy("us_stocks", "news", strategy="free_first")
    us_news_codes = _codes(us_news)

    assert DataSourceCode.FINNHUB in us_news_codes
    assert DataSourceCode.ALPHA_VANTAGE in us_news_codes
    assert DataSourceCode.GROK_X not in us_news_codes
    assert DataSourceCode.TUSHARE not in us_news_codes
    assert DataSourceCode.WIND not in us_news_codes


def test_quality_first_strategy_allows_grok_x_without_premium_sources():
    hk_news = list_data_sources_for_strategy("hk_stocks", "news", strategy="quality_first")
    hk_news_codes = _codes(hk_news)

    assert DataSourceCode.GROK_X in hk_news_codes
    assert DataSourceCode.AKSHARE in hk_news_codes
    assert DataSourceCode.WIND not in hk_news_codes


def test_premium_enhanced_strategy_can_include_paid_enhancement_sources():
    a_share_news = list_data_sources_for_strategy("a_shares", "news", strategy="premium_enhanced")
    a_share_news_codes = _codes(a_share_news)

    assert DataSourceCode.AKSHARE in a_share_news_codes
    assert DataSourceCode.GROK_X in a_share_news_codes
    assert DataSourceCode.TUSHARE in a_share_news_codes
    assert DataSourceCode.WIND in a_share_news_codes
    assert DataSourceCode.CHOICE in a_share_news_codes


def test_unknown_data_source_strategy_is_rejected():
    try:
        list_data_sources_for_strategy("us_stocks", "news", strategy="unknown")
    except ValueError as exc:
        assert "Unsupported data source strategy" in str(exc)
    else:
        raise AssertionError("unknown strategy should raise ValueError")
