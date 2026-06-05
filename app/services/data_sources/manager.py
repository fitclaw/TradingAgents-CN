"""
Data source manager that orchestrates multiple adapters with priority and optional consistency checks
"""
import os
from typing import List, Optional, Tuple, Dict
import logging
from datetime import datetime, timedelta
import pandas as pd

from tradingagents.constants import list_data_sources_for_strategy
from .base import DataSourceAdapter
from .tushare_adapter import TushareAdapter
from .akshare_adapter import AKShareAdapter
from .baostock_adapter import BaoStockAdapter

logger = logging.getLogger(__name__)

SUPPORTED_DATA_SOURCE_STRATEGIES = {"free_first", "quality_first", "premium_enhanced"}


class DataSourceManager:
    """
    数据源管理器
    - 管理多个适配器，基于优先级排序
    - 提供 fallback 获取能力
    - 可选：一致性检查（若依赖存在）
    """

    def __init__(self, strategy: Optional[str] = None):
        self.strategy = self._resolve_strategy(strategy)
        self.adapters: List[DataSourceAdapter] = [
            TushareAdapter(),
            AKShareAdapter(),
            BaoStockAdapter(),
        ]

        # 从数据库加载优先级配置
        self._load_priority_from_database()

        # 按优先级排序（数字越大优先级越高，所以降序排列）
        self.adapters.sort(key=lambda x: x.priority, reverse=True)
        logger.info(f"📊 数据源策略: {self.strategy}")

        try:
            from .data_consistency_checker import DataConsistencyChecker  # type: ignore
            self.consistency_checker = DataConsistencyChecker()
        except Exception:
            logger.warning("⚠️ 数据一致性检查器不可用")
            self.consistency_checker = None

    def _resolve_strategy(self, strategy: Optional[str]) -> str:
        """解析数据源策略，默认使用免费优先。"""
        raw_strategy = strategy or os.getenv("TA_DATA_SOURCE_STRATEGY", "free_first")
        normalized = str(raw_strategy or "").strip().lower()
        if normalized in SUPPORTED_DATA_SOURCE_STRATEGIES:
            return normalized

        logger.warning(
            "⚠️ 不支持的数据源策略 %s，回退到 free_first。可选值: %s",
            raw_strategy,
            sorted(SUPPORTED_DATA_SOURCE_STRATEGIES),
        )
        return "free_first"

    def _get_ordered_available_adapters(
        self,
        capability: str,
        preferred_sources: Optional[List[str]] = None,
    ) -> List[DataSourceAdapter]:
        """
        根据数据源策略、能力和可用性排序 adapter。

        free_first 不会静默启用 premium_optional 数据源；如果需要 Tushare 等付费增强源，
        调用方应显式使用 premium_enhanced 策略。
        """
        available_adapters = self.get_available_adapters()
        available_by_name = {adapter.name.lower(): adapter for adapter in available_adapters}

        strategy_sources = list_data_sources_for_strategy(
            market="a_shares",
            capability=capability,
            strategy=self.strategy,
        )
        strategy_order = [
            str(info.code.value if hasattr(info.code, "value") else info.code).lower()
            for info in strategy_sources
        ]

        preferred_order = [
            str(source).strip().lower()
            for source in (preferred_sources or [])
            if str(source).strip()
        ]
        if preferred_order:
            skipped = [source for source in preferred_order if source not in strategy_order]
            if skipped:
                logger.info(
                    "📊 数据源策略 %s 跳过不在 %s/%s 策略链中的优先源: %s",
                    self.strategy,
                    "a_shares",
                    capability,
                    skipped,
                )
            ordered_names = [
                source for source in preferred_order
                if source in strategy_order and source in available_by_name
            ]
            ordered_names.extend(
                source for source in strategy_order
                if source not in ordered_names and source in available_by_name
            )
        else:
            ordered_names = [
                source for source in strategy_order
                if source in available_by_name
            ]

        ordered_adapters = [available_by_name[name] for name in ordered_names]
        logger.info(
            "📊 数据源排序: strategy=%s, capability=%s, adapters=%s",
            self.strategy,
            capability,
            [adapter.name for adapter in ordered_adapters],
        )
        return ordered_adapters

    def _load_priority_from_database(self):
        """从数据库加载数据源优先级配置（从 datasource_groupings 集合读取 A股市场的优先级）"""
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            groupings_collection = db.datasource_groupings

            # 查询 A股市场的数据源分组配置
            groupings = list(groupings_collection.find({
                "market_category_id": "a_shares",
                "enabled": True
            }))

            if groupings:
                # 创建名称到优先级的映射（数据源名称需要转换为小写）
                priority_map = {}
                for grouping in groupings:
                    data_source_name = grouping.get('data_source_name', '').lower()
                    priority = grouping.get('priority')
                    if data_source_name and priority is not None:
                        priority_map[data_source_name] = priority
                        logger.info(f"📊 从数据库读取 {data_source_name} 在 A股市场的优先级: {priority}")

                # 更新各个 Adapter 的优先级
                for adapter in self.adapters:
                    if adapter.name in priority_map:
                        # 动态设置优先级
                        adapter._priority = priority_map[adapter.name]
                        logger.info(f"✅ 设置 {adapter.name} 优先级: {adapter._priority}")
                    else:
                        # 使用默认优先级
                        adapter._priority = adapter._get_default_priority()
                        logger.info(f"⚠️ 数据库中未找到 {adapter.name} 配置，使用默认优先级: {adapter._priority}")
            else:
                logger.info("⚠️ 数据库中未找到 A股市场的数据源配置，使用默认优先级")
                # 使用默认优先级
                for adapter in self.adapters:
                    adapter._priority = adapter._get_default_priority()
        except Exception as e:
            logger.warning(f"⚠️ 从数据库加载优先级失败: {e}，使用默认优先级")
            import traceback
            logger.warning(f"堆栈跟踪:\n{traceback.format_exc()}")
            # 使用默认优先级
            for adapter in self.adapters:
                adapter._priority = adapter._get_default_priority()

    def get_available_adapters(self) -> List[DataSourceAdapter]:
        available: List[DataSourceAdapter] = []
        for adapter in self.adapters:
            if adapter.is_available():
                available.append(adapter)
                logger.info(
                    f"Data source {adapter.name} is available (priority: {adapter.priority})"
                )
            else:
                logger.warning(f"Data source {adapter.name} is not available")
        return available

    def get_stock_list_with_fallback(self, preferred_sources: Optional[List[str]] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        获取股票列表，支持指定优先数据源

        Args:
            preferred_sources: 优先使用的数据源列表，例如 ['akshare', 'baostock']
                             如果为 None，则按照默认优先级顺序

        Returns:
            (DataFrame, source_name) 或 (None, None)
        """
        available_adapters = self._get_ordered_available_adapters("stock_list", preferred_sources)

        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch stock list from {adapter.name}")
                df = adapter.get_stock_list()
                if df is not None and not df.empty:
                    return df, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch stock list from {adapter.name}: {e}")
                continue
        return None, None

    def get_daily_basic_with_fallback(self, trade_date: str, preferred_sources: Optional[List[str]] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        获取每日基础数据，支持指定优先数据源

        Args:
            trade_date: 交易日期
            preferred_sources: 优先使用的数据源列表

        Returns:
            (DataFrame, source_name) 或 (None, None)
        """
        available_adapters = self._get_ordered_available_adapters("fundamentals", preferred_sources)

        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch daily basic data from {adapter.name}")
                df = adapter.get_daily_basic(trade_date)
                if df is not None and not df.empty:
                    return df, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch daily basic data from {adapter.name}: {e}")
                continue
        return None, None

    def find_latest_trade_date_with_fallback(self, preferred_sources: Optional[List[str]] = None) -> Optional[str]:
        """
        查找最新交易日期，支持指定优先数据源

        Args:
            preferred_sources: 优先使用的数据源列表

        Returns:
            交易日期字符串（YYYYMMDD格式）或 None
        """
        available_adapters = self._get_ordered_available_adapters("kline", preferred_sources)

        for adapter in available_adapters:
            try:
                trade_date = adapter.find_latest_trade_date()
                if trade_date:
                    return trade_date
            except Exception as e:
                logger.error(f"Failed to find trade date from {adapter.name}: {e}")
                continue
        return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    def get_realtime_quotes_with_fallback(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        获取全市场实时快照，按适配器优先级依次尝试，返回首个成功结果
        Returns: (quotes_dict, source_name)
        quotes_dict 形如 { '000001': {'close': 10.0, 'pct_chg': 1.2, 'amount': 1.2e8}, ... }
        """
        available_adapters = self._get_ordered_available_adapters("quotes")
        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch realtime quotes from {adapter.name}")
                data = adapter.get_realtime_quotes()
                if data:
                    return data, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch realtime quotes from {adapter.name}: {e}")
                continue
        return None, None


    def get_daily_basic_with_consistency_check(
        self, trade_date: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict]]:
        """
        使用一致性检查获取每日基础数据

        Returns:
            Tuple[DataFrame, source_name, consistency_report]
        """
        available_adapters = self._get_ordered_available_adapters("fundamentals")
        if len(available_adapters) < 2:
            df, source = self.get_daily_basic_with_fallback(trade_date)
            return df, source, None
        primary_adapter = available_adapters[0]
        secondary_adapter = available_adapters[1]
        try:
            logger.info(
                f"🔍 获取数据进行一致性检查: {primary_adapter.name} vs {secondary_adapter.name}"
            )
            primary_data = primary_adapter.get_daily_basic(trade_date)
            secondary_data = secondary_adapter.get_daily_basic(trade_date)
            if primary_data is None or primary_data.empty:
                logger.warning(f"⚠️ 主数据源{primary_adapter.name}失败，使用fallback")
                df, source = self.get_daily_basic_with_fallback(trade_date)
                return df, source, None
            if secondary_data is None or secondary_data.empty:
                logger.warning(f"⚠️ 次数据源{secondary_adapter.name}失败，使用主数据源")
                return primary_data, primary_adapter.name, None
            if self.consistency_checker:
                consistency_result = self.consistency_checker.check_daily_basic_consistency(
                    primary_data,
                    secondary_data,
                    primary_adapter.name,
                    secondary_adapter.name,
                )
                final_data, resolution_strategy = self.consistency_checker.resolve_data_conflicts(
                    primary_data, secondary_data, consistency_result
                )
                consistency_report = {
                    'is_consistent': consistency_result.is_consistent,
                    'confidence_score': consistency_result.confidence_score,
                    'recommended_action': consistency_result.recommended_action,
                    'resolution_strategy': resolution_strategy,
                    'differences': consistency_result.differences,
                    'primary_source': primary_adapter.name,
                    'secondary_source': secondary_adapter.name,
                }
                logger.info(
                    f"📊 数据一致性检查完成: 置信度={consistency_result.confidence_score:.2f}, 策略={consistency_result.recommended_action}"
                )
                return final_data, primary_adapter.name, consistency_report
            else:
                logger.warning("⚠️ 一致性检查器不可用，使用主数据源")
                return primary_data, primary_adapter.name, None
        except Exception as e:
            logger.error(f"❌ 一致性检查失败: {e}")
            df, source = self.get_daily_basic_with_fallback(trade_date)
            return df, source, None



    def get_kline_with_fallback(self, code: str, period: str = "day", limit: int = 120, adj: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """按优先级尝试获取K线，返回(items, source)"""
        available_adapters = self._get_ordered_available_adapters("kline")
        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch kline from {adapter.name}")
                items = adapter.get_kline(code=code, period=period, limit=limit, adj=adj)
                if items:
                    return items, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch kline from {adapter.name}: {e}")
                continue
        return None, None

    def get_news_with_fallback(self, code: str, days: int = 2, limit: int = 50, include_announcements: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """按优先级尝试获取新闻与公告，返回(items, source)"""
        available_adapters = self._get_ordered_available_adapters("news")
        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch news from {adapter.name}")
                items = adapter.get_news(code=code, days=days, limit=limit, include_announcements=include_announcements)
                if items:
                    return items, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch news from {adapter.name}: {e}")
                continue
        return None, None
