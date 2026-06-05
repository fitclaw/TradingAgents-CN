# 免费优先数据源聚合产品计划

## 背景

TradingAgents-CN 当前已经支持多数据源、多市场分析和本地缓存，但不少链路仍默认依赖付费或准付费数据源，且数据源选择逻辑分散在 App 服务、Dataflows、同步任务和 Agent 工具函数中。

本计划的目标不是寻找一个覆盖 A 股、港股、美股的统一 API，而是为 TradingAgents-CN 建立一套质量优先、免费优先的多 API 聚合策略，让系统在不依赖付费数据源的情况下也能完成可信的投研分析。

## 产品目标

1. 以 TradingAgents-CN 为唯一实施核心。
2. 建立免费优先的数据源配置策略，支持无需 key、免费 key、免费额度和低成本信息源的混合使用。
3. 按市场和数据类型聚合多个可信 API，而不是按单一 provider 统一三市场。
4. 把 Grok/X 接入为 news/social 数据源之一，用于公开市场信息、公司事件、情绪和宏观线索采集。
5. 所有数据输出必须保留来源、时间、降级链路、缓存状态和必要限制说明。
6. 付费数据源保留为可选增强，默认不得静默依赖或自动切换到付费源。

## 非目标

1. 不做实盘交易、券商下单或无人值守交易决策。
2. 不把 Grok/X 作为行情、财务或官方公告 API。
3. 不保证免费源具备生产级 SLA。
4. 不承诺单一 provider 覆盖所有市场和所有数据类型。

## 数据源分级

| 等级 | 定义 | 默认策略 |
| --- | --- | --- |
| free_no_key | 完全免费、无需 key | 可默认启用 |
| free_key | 免费 key 或免费额度 | 可默认推荐，用户配置 key 后启用 |
| low_cost | 低成本但非免费，如 Grok 模型用于 X 信息采集 | 作为增强型 news/social 源 |
| premium_optional | 明确付费或高权限数据源 | 可保留配置，不默认依赖 |
| local_cache | MongoDB 或本地文件缓存 | 最高优先级，承载复现和降级 |

## 市场与数据类型策略

### A 股

| 数据类型 | 推荐链路 |
| --- | --- |
| 股票列表 | MongoDB -> AKShare -> BaoStock -> Tushare optional |
| 日/周/月 K 线 | MongoDB -> AKShare -> BaoStock -> Tushare optional |
| 实时行情 | MongoDB 最新快照 -> AKShare -> Tushare free/optional |
| 基本面/财务 | MongoDB -> AKShare/BaoStock -> Tushare optional |
| 新闻/公告 | MongoDB -> AKShare/公开新闻 -> Grok/X 补充 |

### 港股

| 数据类型 | 推荐链路 |
| --- | --- |
| 股票基础信息 | MongoDB -> 本地映射缓存 -> AKShare -> yfinance |
| K 线/行情 | MongoDB -> yfinance -> AKShare -> 免费额度源 optional |
| 基本面 | MongoDB -> yfinance -> 免费额度源 optional |
| 新闻/社媒 | MongoDB -> Grok/X -> Google/公开新闻 |

### 美股

| 数据类型 | 推荐链路 |
| --- | --- |
| K 线/行情 | MongoDB -> yfinance -> Alpha Vantage/Finnhub free tier optional |
| 基本面 | MongoDB -> SEC EDGAR -> yfinance -> Finnhub/FMP free tier optional |
| 新闻 | MongoDB -> Grok/X -> Google/公开新闻 -> Finnhub free tier optional |
| 社媒/市场情绪 | MongoDB -> Grok/X -> Reddit/StockTwits optional |
| 宏观市场 | MongoDB -> FRED/公开源 -> Grok/X 补充 |

## Grok/X Provider 定位

Grok/X 是 news/social 数据源，不是行情源。

输入：
- ticker、公司名、市场、宏观主题、时间窗口
- 可选可信账号白名单、关键词、语言

输出：
- `title`
- `summary`
- `source_account`
- `source_url`
- `published_at`
- `market`
- `symbols`
- `topic`
- `sentiment`
- `confidence`
- `evidence`

基本约束：
- 必须保留来源链接和发布时间。
- 不把 X 信息直接当成事实结论。
- 对监管、财报、并购、停牌等高影响信息，应提示需要官方来源二次确认。
- 默认进入 news analyst 和 social analyst，不直接进入交易决策。

## 配置模式

### free_first

优先使用无需 key 和免费 key 数据源。付费源即使配置存在，也不参与自动降级，除非用户显式启用。

### quality_first

在免费/低成本约束下优先选质量更高的数据源。允许免费额度 key 和 Grok/X 参与，但必须记录成本和额度风险。

### premium_enhanced

用户显式启用后，允许 Tushare 高权限、Finnhub 付费、Wind、Choice 等高级源参与。

## 实施阶段

### 阶段 1：审计和元数据

目标：
- 标记现有数据源的访问成本、免费层、能力、市场覆盖和默认角色。
- 统一数据源注册表，先不大规模改业务逻辑。
- 输出当前付费/准付费依赖清单。

验收：
- 数据源注册表能区分 free_no_key、free_key、low_cost、premium_optional、local_cache。
- `Grok/X` 和 `SEC EDGAR` 作为候选数据源出现在注册表中。
- 文档和测试覆盖核心数据源分级。

### 阶段 2：策略选择器

目标：
- 增加按市场、能力、配置模式选择 provider 的策略函数。
- 修正 App 层和 Dataflows 层优先级语义不一致问题。
- 禁止 free_first 模式静默切换到付费源。

验收：
- 固定样本能返回清晰的 provider chain。
- 所有返回结果包含 `source`、`source_chain`、`is_cache_hit` 和 `warnings`。

### 阶段 3：Grok/X News/Social Provider

目标：
- 将 Grok/X 接入为标准 news/social provider。
- 输出结构化消息项，供 news analyst 和 social analyst 使用。
- 支持可信账号和关键词配置。

验收：
- 美股、港股、宏观主题各能生成结构化消息列表。
- 报告中保留来源链接和时间。
- 高影响信息带二次验证提示。

### 阶段 4：免费源替换和回归

目标：
- 按数据类型逐步替换默认付费依赖。
- 建立 A 股、港股、美股固定样本回归。
- 补充限流、失败降级、缓存命中测试。

验收样本：
- A 股：600519、000001、300750
- 港股：0700.HK、9988.HK
- 美股：AAPL、MSFT、NVDA
- 宏观：美元指数、10 年期美债、纳指、恒生科技

## 风险

1. 免费源稳定性和字段口径不一致，需要缓存和审计链路兜底。
2. yfinance、AKShare 等非官方源需明确使用边界。
3. Grok/X 信息有噪声，必须保留来源和置信度。
4. 免费额度源可能因限流导致结果不稳定，需要配置限流和降级。
5. 付费源如果继续保留在配置中，必须避免被 free_first 模式自动调用。

## 首批实现范围

本分支先完成：
- 产品计划文档。
- 数据源注册表成本分级与能力元数据。
- 新增 Grok/X、SEC EDGAR 候选数据源。
- 针对注册表的轻量测试。

