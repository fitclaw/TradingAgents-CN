"""
数据源编码统一定义
所有数据源的编码、名称、描述等信息都在这里定义

添加新数据源的步骤：
1. 在 DataSourceCode 枚举中添加新的数据源编码
2. 在 DATA_SOURCE_REGISTRY 中注册数据源信息
3. 在对应的 provider 中实现数据源接口
4. 更新前端的数据源类型选项（如果需要）
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class DataSourceCode(str, Enum):
    """
    数据源编码枚举
    
    命名规范：
    - 使用大写字母和下划线
    - 值使用小写字母和下划线
    - 保持简洁明了
    """
    
    # ==================== 缓存数据源 ====================
    MONGODB = "mongodb"  # MongoDB 数据库缓存（最高优先级）
    
    # ==================== 中国市场数据源 ====================
    TUSHARE = "tushare"      # Tushare - 专业A股数据
    AKSHARE = "akshare"      # AKShare - 开源金融数据（A股+港股）
    BAOSTOCK = "baostock"    # BaoStock - 免费A股数据
    
    # ==================== 美股数据源 ====================
    YFINANCE = "yfinance"         # yfinance - Yahoo Finance Python库
    FINNHUB = "finnhub"           # Finnhub - 美股实时数据
    YAHOO_FINANCE = "yahoo_finance"  # Yahoo Finance - 全球股票数据（别名）
    ALPHA_VANTAGE = "alpha_vantage"  # Alpha Vantage - 美股技术分析
    SEC_EDGAR = "sec_edgar"     # SEC EDGAR - 官方美股公司披露与财务事实
    IEX_CLOUD = "iex_cloud"       # IEX Cloud - 美股实时数据

    # ==================== 新闻/社媒/宏观数据源 ====================
    GROK_X = "grok_x"  # Grok/X - X公开信息抓取与结构化整理

    # ==================== 港股数据源 ====================
    # 注意：AKShare 也支持港股，已在上面定义
    
    # ==================== 专业数据源 ====================
    WIND = "wind"        # Wind 万得 - 专业金融终端
    CHOICE = "choice"    # 东方财富 Choice - 专业金融数据
    
    # ==================== 其他数据源 ====================
    QUANDL = "quandl"        # Quandl - 经济和金融数据
    LOCAL_FILE = "local_file"  # 本地文件数据源
    CUSTOM = "custom"        # 自定义数据源


@dataclass
class DataSourceInfo:
    """数据源信息"""
    code: str  # 数据源编码
    name: str  # 数据源名称
    display_name: str  # 显示名称
    provider: str  # 提供商
    description: str  # 描述
    supported_markets: List[str]  # 支持的市场（a_shares, us_stocks, hk_stocks, etc.）
    requires_api_key: bool  # 是否需要 API 密钥
    is_free: bool  # 是否免费
    access_tier: str = "free_no_key"  # local_cache/free_no_key/free_key/low_cost/premium_optional
    default_role: str = "fallback"  # primary/default/fallback/optional_enhancement/premium_enhancement
    capabilities: List[str] = None  # 标准能力：quotes/kline/fundamentals/news/social/macro/filings/cache
    free_tier_note: Optional[str] = None  # 免费额度或免费能力说明
    rate_limit_note: Optional[str] = None  # 频率限制说明
    license_note: Optional[str] = None  # 授权与使用边界说明
    quality_note: Optional[str] = None  # 数据质量说明
    official_website: Optional[str] = None  # 官方网站
    documentation_url: Optional[str] = None  # 文档地址
    features: List[str] = None  # 特性列表
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.features is None:
            self.features = []


# ==================== 数据源注册表 ====================
DATA_SOURCE_REGISTRY: Dict[str, DataSourceInfo] = {
    # MongoDB 缓存
    DataSourceCode.MONGODB: DataSourceInfo(
        code=DataSourceCode.MONGODB,
        name="MongoDB",
        display_name="MongoDB 缓存",
        provider="MongoDB Inc.",
        description="本地 MongoDB 数据库缓存，最高优先级数据源",
        supported_markets=["a_shares", "us_stocks", "hk_stocks", "crypto", "futures"],
        requires_api_key=False,
        is_free=True,
        access_tier="local_cache",
        default_role="primary",
        capabilities=["cache", "quotes", "kline", "fundamentals", "news", "social", "macro"],
        quality_note="本地缓存优先用于复现、降级和减少外部API依赖，质量取决于同步任务和来源链路。",
        features=["本地缓存", "最快速度", "离线可用"],
    ),
    
    # Tushare
    DataSourceCode.TUSHARE: DataSourceInfo(
        code=DataSourceCode.TUSHARE,
        name="Tushare",
        display_name="Tushare",
        provider="Tushare",
        description="专业的A股数据接口，提供高质量的历史数据和实时行情",
        supported_markets=["a_shares"],
        requires_api_key=True,
        is_free=False,  # 免费版有限制，专业版需付费
        access_tier="premium_optional",
        default_role="premium_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news"],
        free_tier_note="存在 token 和积分门槛；部分基础接口可用，高频、实时或高级数据通常需要更高权限。",
        rate_limit_note="按接口和账号权限限制，需在配置中显式限流。",
        quality_note="A股数据质量较高，但不应在免费优先模式中静默作为默认依赖。",
        official_website="https://tushare.pro",
        documentation_url="https://tushare.pro/document/2",
        features=["历史行情", "实时行情", "财务数据", "基本面数据", "新闻公告"],
    ),
    
    # AKShare
    DataSourceCode.AKSHARE: DataSourceInfo(
        code=DataSourceCode.AKSHARE,
        name="AKShare",
        display_name="AKShare",
        provider="AKFamily",
        description="开源的金融数据接口，支持A股和港股，完全免费",
        supported_markets=["a_shares", "hk_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="default",
        capabilities=["quotes", "kline", "fundamentals", "news"],
        free_tier_note="开源免费，无需API key。",
        rate_limit_note="可能受上游站点频率和反爬策略影响，批量同步需要限流和缓存。",
        quality_note="覆盖广，适合免费优先默认源；字段口径需按接口标准化。",
        official_website="https://akshare.akfamily.xyz",
        documentation_url="https://akshare.akfamily.xyz/introduction.html",
        features=["历史行情", "实时行情", "财务数据", "新闻资讯", "完全免费"],
    ),
    
    # BaoStock
    DataSourceCode.BAOSTOCK: DataSourceInfo(
        code=DataSourceCode.BAOSTOCK,
        name="BaoStock",
        display_name="BaoStock",
        provider="BaoStock",
        description="免费的A股数据接口，提供稳定的历史数据",
        supported_markets=["a_shares"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="fallback",
        capabilities=["kline", "fundamentals"],
        free_tier_note="免费、无需API key。",
        quality_note="适合A股历史行情和部分财务数据兜底，不适合作为实时行情源。",
        official_website="http://baostock.com",
        documentation_url="http://baostock.com/baostock/index.php/Python_API%E6%96%87%E6%A1%A3",
        features=["历史行情", "财务数据", "完全免费", "数据稳定"],
    ),
    
    # yfinance
    DataSourceCode.YFINANCE: DataSourceInfo(
        code=DataSourceCode.YFINANCE,
        name="yfinance",
        display_name="yfinance (Yahoo Finance)",
        provider="Yahoo Finance",
        description="Yahoo Finance Python库，支持美股、港股等多个市场，完全免费",
        supported_markets=["us_stocks", "hk_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="default",
        capabilities=["quotes", "kline", "fundamentals"],
        free_tier_note="免费、无需API key。",
        rate_limit_note="非官方封装，可能受Yahoo Finance接口变化和频率限制影响。",
        license_note="适合研究和个人使用；生产或商业使用需自行确认Yahoo Finance条款。",
        quality_note="美股/港股价格数据覆盖好，基本面字段可能不稳定。",
        official_website="https://finance.yahoo.com",
        documentation_url="https://pypi.org/project/yfinance/",
        features=["历史行情", "实时行情", "技术指标", "全球市场", "完全免费"],
    ),

    # Finnhub
    DataSourceCode.FINNHUB: DataSourceInfo(
        code=DataSourceCode.FINNHUB,
        name="Finnhub",
        display_name="Finnhub",
        provider="Finnhub",
        description="美股实时数据和新闻接口，提供高质量的市场数据",
        supported_markets=["us_stocks"],
        requires_api_key=True,
        is_free=True,  # 有免费版
        access_tier="free_key",
        default_role="optional_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news"],
        free_tier_note="提供免费API key和免费额度，超出后需升级。",
        rate_limit_note="免费层有调用频率限制，适合单票补充和新闻兜底。",
        quality_note="结构化程度较好，但免费额度不适合大规模同步。",
        official_website="https://finnhub.io",
        documentation_url="https://finnhub.io/docs/api",
        features=["实时行情", "历史数据", "新闻资讯", "财务数据", "技术指标"],
    ),
    
    # Yahoo Finance
    DataSourceCode.YAHOO_FINANCE: DataSourceInfo(
        code=DataSourceCode.YAHOO_FINANCE,
        name="Yahoo Finance",
        display_name="Yahoo Finance",
        provider="Yahoo",
        description="全球股票数据接口，支持美股、港股等多个市场",
        supported_markets=["us_stocks", "hk_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="fallback",
        capabilities=["quotes", "kline", "fundamentals"],
        free_tier_note="免费、无需API key；本项目优先通过 yfinance 封装访问。",
        license_note="适合研究和个人使用；生产或商业使用需自行确认Yahoo Finance条款。",
        official_website="https://finance.yahoo.com",
        features=["历史行情", "实时行情", "全球市场", "完全免费"],
    ),
    
    # Alpha Vantage
    DataSourceCode.ALPHA_VANTAGE: DataSourceInfo(
        code=DataSourceCode.ALPHA_VANTAGE,
        name="Alpha Vantage",
        display_name="Alpha Vantage",
        provider="Alpha Vantage",
        description="美股技术分析数据接口，提供丰富的技术指标",
        supported_markets=["us_stocks"],
        requires_api_key=True,
        is_free=True,  # 有免费版
        access_tier="free_key",
        default_role="optional_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news", "macro"],
        free_tier_note="提供免费API key和有限免费额度。",
        rate_limit_note="免费层调用频率较低，适合单票和低频补充。",
        quality_note="技术指标和美股基础数据较易接入，但批量分析需缓存。",
        official_website="https://www.alphavantage.co",
        documentation_url="https://www.alphavantage.co/documentation",
        features=["技术指标", "历史数据", "外汇数据", "加密货币"],
    ),

    # SEC EDGAR
    DataSourceCode.SEC_EDGAR: DataSourceInfo(
        code=DataSourceCode.SEC_EDGAR,
        name="SEC EDGAR",
        display_name="SEC EDGAR",
        provider="U.S. Securities and Exchange Commission",
        description="美国SEC官方公司披露、filings和company facts数据源",
        supported_markets=["us_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="default",
        capabilities=["filings", "fundamentals"],
        free_tier_note="官方免费接口，无需API key。",
        rate_limit_note="需要遵守SEC fair access和User-Agent要求。",
        quality_note="美股官方披露可信度高，适合基本面事实和财报二次验证。",
        official_website="https://www.sec.gov",
        documentation_url="https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        features=["官方披露", "财务事实", "公司档案", "完全免费"],
    ),
    
    # IEX Cloud
    DataSourceCode.IEX_CLOUD: DataSourceInfo(
        code=DataSourceCode.IEX_CLOUD,
        name="IEX Cloud",
        display_name="IEX Cloud",
        provider="IEX Cloud",
        description="美股实时数据接口，提供高质量的市场数据",
        supported_markets=["us_stocks"],
        requires_api_key=True,
        is_free=False,  # 需付费
        access_tier="premium_optional",
        default_role="premium_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news"],
        quality_note="付费增强源，不参与免费优先默认降级。",
        official_website="https://iexcloud.io",
        documentation_url="https://iexcloud.io/docs/api",
        features=["实时行情", "历史数据", "财务数据", "新闻资讯"],
    ),
    
    # Wind
    DataSourceCode.WIND: DataSourceInfo(
        code=DataSourceCode.WIND,
        name="Wind",
        display_name="Wind 万得",
        provider="Wind 万得",
        description="专业金融终端，提供全面的金融数据和分析工具",
        supported_markets=["a_shares", "hk_stocks", "us_stocks"],
        requires_api_key=True,
        is_free=False,  # 专业版需付费
        access_tier="premium_optional",
        default_role="premium_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news", "macro"],
        quality_note="专业终端数据源，保留为显式付费增强，不参与免费优先默认降级。",
        official_website="https://www.wind.com.cn",
        features=["专业数据", "全市场覆盖", "高质量数据", "专业分析"],
    ),
    
    # Choice
    DataSourceCode.CHOICE: DataSourceInfo(
        code=DataSourceCode.CHOICE,
        name="Choice",
        display_name="东方财富 Choice",
        provider="东方财富",
        description="专业金融数据终端，提供全面的A股数据",
        supported_markets=["a_shares"],
        requires_api_key=True,
        is_free=False,  # 专业版需付费
        access_tier="premium_optional",
        default_role="premium_enhancement",
        capabilities=["quotes", "kline", "fundamentals", "news"],
        quality_note="专业终端数据源，保留为显式付费增强，不参与免费优先默认降级。",
        official_website="http://choice.eastmoney.com",
        features=["专业数据", "A股专注", "高质量数据", "专业分析"],
    ),

    # Grok/X
    DataSourceCode.GROK_X: DataSourceInfo(
        code=DataSourceCode.GROK_X,
        name="Grok/X",
        display_name="Grok/X",
        provider="xAI / X",
        description="使用便宜的Grok模型抓取并结构化X上的公开市场信息",
        supported_markets=["a_shares", "hk_stocks", "us_stocks", "macro"],
        requires_api_key=True,
        is_free=False,
        access_tier="low_cost",
        default_role="optional_enhancement",
        capabilities=["news", "social", "macro"],
        free_tier_note="低成本模型调用，不视为免费API。",
        rate_limit_note="受Grok模型和X可访问性限制，应配置缓存、时间窗口和可信账号白名单。",
        license_note="只作为公开信息检索与摘要源；高影响事件需官方来源二次确认。",
        quality_note="适合捕捉美股、港股和宏观市场的X实时线索，不适合作为行情或财务事实源。",
        official_website="https://x.ai",
        documentation_url="https://docs.x.ai",
        features=["X信息抓取", "新闻线索", "社媒情绪", "宏观线索", "结构化摘要"],
    ),
    
    # Quandl
    DataSourceCode.QUANDL: DataSourceInfo(
        code=DataSourceCode.QUANDL,
        name="Quandl",
        display_name="Quandl",
        provider="Nasdaq",
        description="经济和金融数据平台，提供全球经济数据",
        supported_markets=["us_stocks"],
        requires_api_key=True,
        is_free=True,  # 有免费版
        access_tier="free_key",
        default_role="optional_enhancement",
        capabilities=["fundamentals", "macro"],
        free_tier_note="部分数据集免费，很多高质量数据集需要订阅。",
        quality_note="适合经济与金融补充数据，需按具体数据集确认授权和费用。",
        official_website="https://www.quandl.com",
        documentation_url="https://docs.quandl.com",
        features=["经济数据", "金融数据", "全球覆盖"],
    ),
    
    # Local File
    DataSourceCode.LOCAL_FILE: DataSourceInfo(
        code=DataSourceCode.LOCAL_FILE,
        name="Local File",
        display_name="本地文件",
        provider="本地",
        description="从本地文件读取数据",
        supported_markets=["a_shares", "us_stocks", "hk_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="local_cache",
        default_role="primary",
        capabilities=["cache", "quotes", "kline", "fundamentals", "news", "social", "macro"],
        quality_note="适合导入第三方快照和离线回归，质量取决于文件来源和字段映射。",
        features=["离线可用", "自定义数据", "完全免费"],
    ),
    
    # Custom
    DataSourceCode.CUSTOM: DataSourceInfo(
        code=DataSourceCode.CUSTOM,
        name="Custom",
        display_name="自定义数据源",
        provider="自定义",
        description="自定义数据源接口",
        supported_markets=["a_shares", "us_stocks", "hk_stocks"],
        requires_api_key=False,
        is_free=True,
        access_tier="free_no_key",
        default_role="fallback",
        capabilities=["quotes", "kline", "fundamentals", "news", "social", "macro"],
        quality_note="自定义扩展入口，默认不代表可信源；需要接入方声明来源和授权。",
        features=["自定义接口", "灵活配置"],
    ),
}

DATA_SOURCE_STRATEGY_TIERS: Dict[str, List[str]] = {
    "free_first": ["local_cache", "free_no_key", "free_key"],
    "quality_first": ["local_cache", "free_no_key", "free_key", "low_cost"],
    "premium_enhanced": ["local_cache", "free_no_key", "free_key", "low_cost", "premium_optional"],
}

DATA_SOURCE_ROLE_ORDER: Dict[str, int] = {
    "primary": 0,
    "default": 1,
    "fallback": 2,
    "optional_enhancement": 3,
    "premium_enhancement": 4,
}

DATA_SOURCE_ACCESS_TIER_ORDER: Dict[str, int] = {
    "local_cache": 0,
    "free_no_key": 1,
    "free_key": 2,
    "low_cost": 3,
    "premium_optional": 4,
}


# ==================== 辅助函数 ====================

def get_data_source_info(code: str) -> Optional[DataSourceInfo]:
    """
    获取数据源信息
    
    Args:
        code: 数据源编码
    
    Returns:
        数据源信息，如果不存在则返回 None
    """
    return DATA_SOURCE_REGISTRY.get(code)


def list_all_data_sources() -> List[DataSourceInfo]:
    """
    列出所有数据源
    
    Returns:
        所有数据源信息列表
    """
    return list(DATA_SOURCE_REGISTRY.values())


def list_data_sources_by_market(market: str) -> List[DataSourceInfo]:
    """
    列出支持指定市场的数据源
    
    Args:
        market: 市场类型（a_shares, us_stocks, hk_stocks, etc.）
    
    Returns:
        支持该市场的数据源列表
    """
    return [
        info for info in DATA_SOURCE_REGISTRY.values()
        if market in info.supported_markets
    ]


def list_free_data_sources() -> List[DataSourceInfo]:
    """
    列出所有免费数据源
    
    Returns:
        免费数据源列表
    """
    return [
        info for info in DATA_SOURCE_REGISTRY.values()
        if info.is_free
    ]


def list_data_sources_by_access_tier(access_tier: str) -> List[DataSourceInfo]:
    """
    按访问成本等级列出数据源

    Args:
        access_tier: local_cache/free_no_key/free_key/low_cost/premium_optional

    Returns:
        匹配成本等级的数据源列表
    """
    return [
        info for info in DATA_SOURCE_REGISTRY.values()
        if info.access_tier == access_tier
    ]


def list_data_sources_by_capability(capability: str) -> List[DataSourceInfo]:
    """
    按标准能力列出数据源

    Args:
        capability: quotes/kline/fundamentals/news/social/macro/filings/cache

    Returns:
        支持该能力的数据源列表
    """
    return [
        info for info in DATA_SOURCE_REGISTRY.values()
        if capability in info.capabilities
    ]


def list_data_sources_by_market_and_capability(market: str, capability: str) -> List[DataSourceInfo]:
    """
    按市场和标准能力列出数据源

    Args:
        market: 市场类型（a_shares, us_stocks, hk_stocks, macro 等）
        capability: quotes/kline/fundamentals/news/social/macro/filings/cache

    Returns:
        同时支持指定市场和能力的数据源列表
    """
    return [
        info for info in DATA_SOURCE_REGISTRY.values()
        if market in info.supported_markets and capability in info.capabilities
    ]


def list_data_sources_for_strategy(
    market: str,
    capability: str,
    strategy: str = "free_first",
) -> List[DataSourceInfo]:
    """
    按市场、能力和配置策略列出候选数据源

    Args:
        market: 市场类型（a_shares, us_stocks, hk_stocks, macro 等）
        capability: quotes/kline/fundamentals/news/social/macro/filings/cache
        strategy: free_first/quality_first/premium_enhanced

    Returns:
        按默认角色和访问成本排序后的候选数据源列表
    """
    allowed_tiers = DATA_SOURCE_STRATEGY_TIERS.get(strategy)
    if allowed_tiers is None:
        raise ValueError(f"Unsupported data source strategy: {strategy}")

    candidates = [
        info for info in DATA_SOURCE_REGISTRY.values()
        if (
            market in info.supported_markets
            and capability in info.capabilities
            and info.access_tier in allowed_tiers
        )
    ]

    return sorted(
        candidates,
        key=lambda info: (
            DATA_SOURCE_ROLE_ORDER.get(info.default_role, 99),
            DATA_SOURCE_ACCESS_TIER_ORDER.get(info.access_tier, 99),
            info.display_name,
        ),
    )


def is_data_source_supported(code: str) -> bool:
    """
    检查数据源是否支持
    
    Args:
        code: 数据源编码
    
    Returns:
        是否支持
    """
    return code in DATA_SOURCE_REGISTRY
