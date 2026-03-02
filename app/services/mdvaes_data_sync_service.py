"""MDVAES 数据同步服务 - 从 Tushare 同步数据到 MongoDB"""

import logging
import asyncio
import random
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts
from app.core.config import settings
from app.core.database import get_mongo_db

# Tushare API 重试机制
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)
import requests
from requests.exceptions import Timeout, ConnectionError

logger = logging.getLogger(__name__)


class RateLimiter:
    """滑动窗口限流器

    用于限制 API 调用频率，避免超过 Tushare 的访问限制。

    Args:
        max_calls: 时间窗口内允许的最大调用次数
        window_seconds: 时间窗口大小（秒）
    """

    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []  # 存储每次调用的时间戳
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取调用许可，如果超过限制则等待

        使用滑动窗口算法：
        - 移除窗口外的旧调用记录
        - 如果当前窗口内调用次数达到上限，则等待
        - 记录本次调用时间
        """
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)

            # 移除窗口外的旧调用记录
            self.calls = [call_time for call_time in self.calls if call_time > window_start]

            # 检查是否超过限制
            if len(self.calls) >= self.max_calls:
                # 计算需要等待的时间（窗口内最早调用的过期时间）
                oldest_call = self.calls[0]
                wait_time = (oldest_call + timedelta(seconds=self.window_seconds) - now).total_seconds()
                if wait_time > 0:
                    logger.debug(
                        f"🚦 [限流] 达到上限 ({self.max_calls}次/{self.window_seconds}秒)，"
                        f"等待 {wait_time:.2f} 秒..."
                    )
                    await asyncio.sleep(wait_time)
                    # 等待后再次清理旧记录
                    window_start = datetime.now() - timedelta(seconds=self.window_seconds)
                    self.calls = [call_time for call_time in self.calls if call_time > window_start]

            # 记录本次调用
            self.calls.append(now)
            logger.debug(
                f"🚦 [限流] 当前窗口调用次数: {len(self.calls)}/{self.max_calls}"
            )


class MDVAESDataSyncService:
    """MDVAES 数据同步服务"""

    # Tushare 接口限流配置
    RATE_LIMITS = {
        "fina_indicator": (180, 60),  # 每分钟180次
        "daily_basic": (180, 60),     # 每分钟180次
        "stock_basic": (180, 60),     # 每分钟180次
        "default": (180, 60)           # 默认每分钟180次
    }

    def __init__(self):
        # 🔥 修复：动态获取 Tushare Token，优先使用数据库配置
        self._pro = None  # 延迟初始化
        # 为每个接口创建独立的限流器
        self._limiters = {}
        for api_name, (max_calls, window) in self.RATE_LIMITS.items():
            self._limiters[api_name] = RateLimiter(max_calls, window)

    @property
    def pro(self):
        """动态获取 Tushare API 客户端，确保使用最新的 token"""
        if self._pro is None:
            # 🔥 优先级：数据库配置 > 环境变量
            token = self._get_tushare_token()
            self._pro = ts.pro_api(token)
            logger.info(f"📌 初始化 Tushare API 客户端 (token长度: {len(token)})")
        return self._pro

    def _get_tushare_token(self) -> str:
        """
        获取 Tushare Token

        优先级：
        1. 数据库配置（system_configs 集合中的 tushare 数据源配置）
        2. 环境变量（.env 文件中的 TUSHARE_TOKEN）
        """
        import os
        from pymongo import MongoClient
        from app.core.config import settings

        # 1. 尝试从数据库获取
        try:
            client = MongoClient(settings.mongodb_url)
            db = client[settings.mongodb_database]
            config_collection = db.system_configs

            # 查找激活的配置
            config = config_collection.find_one({"is_active": True})
            if config:
                # 查找 tushare 数据源配置
                for ds in config.get("data_source_configs", []):
                    if ds.get("type") == "tushare" or ds.get("type") == "tushare":
                        api_key = ds.get("api_key", "")
                        # 验证 token 有效性
                        if api_key and not api_key.startswith("your_") and len(api_key) > 10:
                            logger.info(f"✅ 使用数据库中的 Tushare Token (长度: {len(api_key)})")
                            client.close()
                            return api_key
                        else:
                            logger.debug(f"⏭️  数据库中 Tushare Token 无效，尝试环境变量")
            client.close()
        except Exception as e:
            logger.warning(f"⚠️  从数据库获取 Tushare Token 失败: {e}")

        # 2. 降级到环境变量
        env_token = os.getenv("TUSHARE_TOKEN", "")
        if env_token and not env_token.startswith("your_"):
            logger.info(f"✅ 使用环境变量中的 Tushare Token (长度: {len(env_token)})")
            return env_token

        # 3. 都没有，抛出异常
        raise ValueError("Tushare Token 未配置！请在数据源配置中设置有效的 API Key")

    def _log_retry_attempt(self, retry_state):
        """记录重试尝试"""
        logger.warning(
            f"🔄 Tushare API 调用失败，正在重试... "
            f"(第 {retry_state.attempt_number} 次，最多 3 次)"
        )

    async def _call_tushare_with_retry(self, func, *args, api_name: str = "default", **kwargs):
        """
        带重试机制和限流的 Tushare API 调用包装器

        Args:
            func: Tushare pro API 方法
            *args, **kwargs: 传递给 API 方法的参数
            api_name: API 名称，用于选择对应的限流器（如 "fina_indicator"）

        Returns:
            API 返回结果

        Raises:
            最后一次失败后的异常
        """
        # 获取对应的限流器
        limiter = self._limiters.get(api_name, self._limiters["default"])

        # 限流：等待获取调用许可
        await limiter.acquire()
        # 定义同步的包装函数（因为 tenacity 需要同步函数）
        def sync_wrapper():
            return func(*args, **kwargs)

        # 使用 tenacity 重试
        # 注意：before_sleep 在每次重试前调用
        retryer = retry(
            stop=stop_after_attempt(3),
            wait=wait_random_exponential(multiplier=1, max=10),
            retry=retry_if_exception_type((Timeout, ConnectionError, OSError, requests.exceptions.RequestException)),
            before_sleep=self._log_retry_attempt,
            reraise=True
        )

        # 在新线程中执行（因为 Tushare API 是同步的）
        try:
            result = await asyncio.to_thread(retryer(sync_wrapper))
            logger.debug(f"✅ Tushare API 调用成功")
            return result
        except Exception as e:
            logger.error(f"❌ Tushare API 调用彻底失败（已重试3次）: {e}")
            raise

    async def sync_daily_data(self, trade_date: str):
        """同步指定交易日的所有 MDVAES 数据"""
        logger.info(f"开始同步 MDVAES 数据: {trade_date}")

        db = get_mongo_db()

        try:
            # 1. 同步分析师盈利预测（使用最近报告日期）
            await self._sync_analyst_forecasts(db, trade_date)

            # 2. 同步每日基本面数据（包含 PE、PB）
            await self._sync_daily_basic(db, trade_date)

            # 3. 同步国债收益率
            await self._sync_bond_yield(db, trade_date)

            # 4. 同步财务比率数据
            await self._sync_financial_ratios(db, trade_date)

            # 5. 同步 EPS 历史数据
            await self._sync_eps_history(db, trade_date)

            logger.info(f"✅ MDVAES 数据同步完成: {trade_date}")
            return {
                "success": True,
                "trade_date": trade_date,
                "synced_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ MDVAES 数据同步失败: {e}", exc_info=True)
            raise

    async def _sync_analyst_forecasts(self, db, report_date: str):
        """同步分析师盈利预测

        Tushare 接口: report_rc (doc_id=292)
        """
        all_forecasts = []
        offset = 0
        limit = 3000

        while True:
            # 使用带重试机制的 Tushare API 调用
            df = await self._call_tushare_with_retry(
                self.pro.report_rc,
                report_date=report_date,
                offset=offset,
                limit=limit
            )

            if df.empty:
                break

            # 转换为字典列表
            records = df.to_dict('records')
            all_forecasts.extend(records)

            offset += limit
            if len(df) < limit:
                break

        if all_forecasts:
            # 批量插入（使用 upsert 避免重复）
            for record in all_forecasts:
                # 构建唯一标识查询条件
                query_filter = {
                    "ts_code": record["ts_code"],
                    "report_date": record["report_date"]
                }
                # 如果有 org_name，也加入查询条件以区分不同机构的报告
                if "org_name" in record and record["org_name"]:
                    query_filter["org_name"] = record["org_name"]

                await db.mdvaes_analyst_forecasts.update_one(
                    query_filter,
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

            logger.info(f"  ✅ 同步分析师预测: {len(all_forecasts)} 条")

    async def _sync_daily_basic(self, db, trade_date: str):
        """同步每日基本面数据（PE、PB 等）

        Tushare 接口: daily_basic (doc_id=32)
        """
        # 获取前 10 个交易日（确保数据完整性）
        start_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=20)).strftime("%Y%m%d")

        # 使用带重试机制的 Tushare API 调用
        df = await self._call_tushare_with_retry(
            self.pro.daily_basic,
            ts_code="",
            start_date=start_date,
            end_date=trade_date,
            fields="ts_code,trade_date,pe,pe_ttm,pb,ps"
        )

        if not df.empty:
            records = df.to_dict('records')

            # 批量插入
            for record in records:
                await db.mdvaes_pe_history.update_one(
                    {
                        "ts_code": record["ts_code"],
                        "trade_date": record["trade_date"]
                    },
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

            logger.info(f"  ✅ 同步每日基本面: {len(records)} 条")

    async def _sync_bond_yield(self, db, trade_date: str):
        """同步国债收益率

        Tushare 接口: yc_cb (doc_id=201)
        获取 10 年期国债收益率
        """
        # 使用带重试机制的 Tushare API 调用
        df = await self._call_tushare_with_retry(
            self.pro.yc_cb,
            ts_code="1001.CB",  # 国债代码
            curve_type="0",      # 到期收益率
            curve_term=10.0,     # 10 年期
            start_date=trade_date,
            end_date=trade_date
        )

        if not df.empty:
            record = df.iloc[0].to_dict()

            await db.mdvaes_bond_rate.update_one(
                {
                    "trade_date": trade_date,
                    "curve_term": 10.0
                },
                {
                    "$set": {
                        **record,
                        "synced_at": datetime.now()
                    }
                },
                upsert=True
            )

            logger.info(f"  ✅ 同步国债收益率: {record['yield']}%")

    async def get_sync_status(self):
        """获取 MDVAES 数据同步状态"""
        db = get_mongo_db()

        # 统计各集合的数据量
        analyst_count = await db.mdvaes_analyst_forecasts.estimated_document_count()
        pe_history_count = await db.mdvaes_pe_history.estimated_document_count()
        bond_rate_count = await db.mdvaes_bond_rate.estimated_document_count()

        # 获取最新同步时间
        latest_analyst = await db.mdvaes_analyst_forecasts.find_one(
            sort=[("synced_at", -1)],
            projection={"synced_at": 1, "_id": 0}
        )
        latest_pe = await db.mdvaes_pe_history.find_one(
            sort=[("synced_at", -1)],
            projection={"synced_at": 1, "_id": 0}
        )
        latest_bond = await db.mdvaes_bond_rate.find_one(
            sort=[("synced_at", -1)],
            projection={"synced_at": 1, "_id": 0}
        )

        return {
            "analyst_forecasts": {
                "count": analyst_count,
                "latest_sync": latest_analyst.get("synced_at") if latest_analyst else None
            },
            "pe_history": {
                "count": pe_history_count,
                "latest_sync": latest_pe.get("synced_at") if latest_pe else None
            },
            "bond_rate": {
                "count": bond_rate_count,
                "latest_sync": latest_bond.get("synced_at") if latest_bond else None
            }
        }

    async def batch_sync_historical_data(
        self,
        start_date: str,
        end_date: str,
        job_id: str = None,
        tables: list[str] = None
    ):
        """批量同步历史数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            job_id: 任务ID（用于进度报告）
            tables: 要同步的表列表，如 ["analyst_forecasts", "pe_history", "bond_rate", "financial_ratios", "eps_history"]

        Returns:
            同步结果统计（包含详细描述）
        """
        # 默认同步所有表
        if tables is None:
            tables = ["analyst_forecasts", "pe_history", "bond_rate", "financial_ratios", "eps_history"]

        # 表名称映射（中文显示）
        table_names = {
            "analyst_forecasts": "分析师盈利预测",
            "pe_history": "PE历史数据",
            "bond_rate": "国债收益率",
            "financial_ratios": "财务比率数据",
            "eps_history": "EPS历史数据"
        }

        logger.info(f"🚀 [批量同步] 开始同步历史数据: {start_date} 至 {end_date}")
        logger.info(f"📋 [批量同步] 选定同步表: {', '.join([table_names.get(t, t) for t in tables])}")

        db = get_mongo_db()

        # 记录每个表的同步状态
        table_status = {}
        detailed_description = []
        detailed_description.append(f"## MDVAES 批量同步任务详情")
        detailed_description.append(f"**时间范围**: {start_date} 至 {end_date}")
        detailed_description.append(f"**选定同步表**: {', '.join([table_names.get(t, t) for t in tables])}")
        detailed_description.append("")
        detailed_description.append("### 同步结果详情")
        detailed_description.append("")

        try:
            # 转换日期格式
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # 根据选定的表执行同步
            total_tables = len(tables)
            current_table_index = 0

            # 1. 批量同步国债收益率
            if "bond_rate" in tables:
                current_table_index += 1
                logger.info("📊 [批量同步] 开始同步国债收益率...")
                try:
                    if job_id:
                        await self._update_progress(job_id, current_table_index * 10, total_tables * 10, f"正在同步国债收益率... ({current_table_index}/{total_tables})")
                    bond_result = await self._batch_sync_bond_yield(db, start_dt, end_dt)
                    table_status["bond_rate"] = {"status": "success", "result": bond_result}
                    detailed_description.append(f"#### ✅ 国债收益率 (mdvaes_bond_rate) - 完成")
                    detailed_description.append(f"- 新增: {bond_result['synced']} 条")
                    detailed_description.append(f"- 更新: {bond_result.get('updated', 0)} 条")
                    detailed_description.append(f"- 跳过: {bond_result['skipped']} 条")
                    logger.info(f"  ✅ 国债收益率同步完成: 新增 {bond_result['synced']} 条, 更新 {bond_result.get('updated', 0)} 条")
                except Exception as e:
                    table_status["bond_rate"] = {"status": "error", "error": str(e)}
                    detailed_description.append(f"#### ❌ 国债收益率 (mdvaes_bond_rate) - 失败")
                    detailed_description.append(f"- 错误原因: {str(e)}")
                    logger.error(f"  ❌ 国债收益率同步失败: {e}")
                detailed_description.append("")
            else:
                detailed_description.append(f"#### ⏭️ 国债收益率 (mdvaes_bond_rate) - 跳过")
                detailed_description.append("")

            # 2. 批量同步每日估值指标
            if "pe_history" in tables:
                current_table_index += 1
                logger.info("📊 [批量同步] 开始同步每日估值指标...")
                try:
                    if job_id:
                        await self._update_progress(job_id, current_table_index * 10, total_tables * 10, f"正在同步每日估值指标... ({current_table_index}/{total_tables})")
                    pe_result = await self._batch_sync_daily_basic(db, start_dt, end_dt)
                    table_status["pe_history"] = {"status": "success", "result": pe_result}
                    detailed_description.append(f"#### ✅ PE历史数据 (mdvaes_pe_history) - 完成")
                    detailed_description.append(f"- 新增: {pe_result['synced']} 条")
                    detailed_description.append(f"- 更新: {pe_result.get('updated', 0)} 条")
                    detailed_description.append(f"- 跳过: {pe_result['skipped']} 条")
                    logger.info(f"  ✅ 每日估值指标同步完成: 新增 {pe_result['synced']} 条, 更新 {pe_result.get('updated', 0)} 条")
                except Exception as e:
                    table_status["pe_history"] = {"status": "error", "error": str(e)}
                    detailed_description.append(f"#### ❌ PE历史数据 (mdvaes_pe_history) - 失败")
                    detailed_description.append(f"- 错误原因: {str(e)}")
                    logger.error(f"  ❌ 每日估值指标同步失败: {e}")
                detailed_description.append("")
            else:
                detailed_description.append(f"#### ⏭️ PE历史数据 (mdvaes_pe_history) - 跳过")
                detailed_description.append("")

            # 3. 批量同步分析师盈利预测
            if "analyst_forecasts" in tables:
                current_table_index += 1
                logger.info("📊 [批量同步] 开始同步分析师盈利预测...")
                try:
                    if job_id:
                        await self._update_progress(job_id, current_table_index * 10, total_tables * 10, f"正在同步分析师盈利预测... ({current_table_index}/{total_tables})")
                    analyst_result = await self._batch_sync_analyst_forecasts(
                        db, start_dt, end_dt, job_id, 10, current_table_index
                    )
                    table_status["analyst_forecasts"] = {"status": "success", "result": analyst_result}
                    detailed_description.append(f"#### ✅ 分析师盈利预测 (mdvaes_analyst_forecasts) - 完成")
                    detailed_description.append(f"- 新增: {analyst_result['synced']} 条")
                    detailed_description.append(f"- 更新: {analyst_result.get('updated', 0)} 条")
                    detailed_description.append(f"- 跳过: {analyst_result['skipped']} 条")
                    logger.info(f"  ✅ 分析师预测同步完成: 新增 {analyst_result['synced']} 条, 更新 {analyst_result.get('updated', 0)} 条")
                except Exception as e:
                    table_status["analyst_forecasts"] = {"status": "error", "error": str(e)}
                    detailed_description.append(f"#### ❌ 分析师盈利预测 (mdvaes_analyst_forecasts) - 失败")
                    detailed_description.append(f"- 错误原因: {str(e)}")
                    logger.error(f"  ❌ 分析师预测同步失败: {e}")
                detailed_description.append("")
            else:
                detailed_description.append(f"#### ⏭️ 分析师盈利预测 (mdvaes_analyst_forecasts) - 跳过")
                detailed_description.append("")

            # 4. 批量同步财务比率数据
            if "financial_ratios" in tables:
                current_table_index += 1
                logger.info("📊 [批量同步] 开始同步财务比率数据...")
                try:
                    if job_id:
                        await self._update_progress(job_id, current_table_index * 10, total_tables * 10, f"正在同步财务比率数据... ({current_table_index}/{total_tables})")
                    ratios_result = await self._batch_sync_financial_ratios(db, start_dt, end_dt)
                    table_status["financial_ratios"] = {"status": "success", "result": ratios_result}
                    detailed_description.append(f"#### ✅ 财务比率数据 (mdvaes_financial_ratios) - 完成")
                    detailed_description.append(f"- 新增: {ratios_result['synced']} 条")
                    detailed_description.append(f"- 更新: {ratios_result.get('updated', 0)} 条")
                    detailed_description.append(f"- 跳过: {ratios_result['skipped']} 条")
                    logger.info(f"  ✅ 财务比率同步完成: 新增 {ratios_result['synced']} 条, 更新 {ratios_result.get('updated', 0)} 条")
                except Exception as e:
                    table_status["financial_ratios"] = {"status": "error", "error": str(e)}
                    detailed_description.append(f"#### ❌ 财务比率数据 (mdvaes_financial_ratios) - 失败")
                    detailed_description.append(f"- 错误原因: {str(e)}")
                    logger.error(f"  ❌ 财务比率同步失败: {e}")
                detailed_description.append("")
            else:
                detailed_description.append(f"#### ⏭️ 财务比率数据 (mdvaes_financial_ratios) - 跳过")
                detailed_description.append("")

            # 5. 批量同步 EPS 历史数据
            if "eps_history" in tables:
                current_table_index += 1
                logger.info("📊 [批量同步] 开始同步 EPS 历史数据...")
                try:
                    if job_id:
                        await self._update_progress(job_id, current_table_index * 10, total_tables * 10, f"正在同步 EPS 历史数据... ({current_table_index}/{total_tables})")
                    eps_result = await self._batch_sync_eps_history(db, start_dt, end_dt)
                    table_status["eps_history"] = {"status": "success", "result": eps_result}
                    detailed_description.append(f"#### ✅ EPS历史数据 (mdvaes_eps_history) - 完成")
                    detailed_description.append(f"- 新增: {eps_result['synced']} 条")
                    detailed_description.append(f"- 更新: {eps_result.get('updated', 0)} 条")
                    detailed_description.append(f"- 跳过: {eps_result['skipped']} 条")
                    logger.info(f"  ✅ EPS 历史同步完成: 新增 {eps_result['synced']} 条, 更新 {eps_result.get('updated', 0)} 条")
                except Exception as e:
                    table_status["eps_history"] = {"status": "error", "error": str(e)}
                    detailed_description.append(f"#### ❌ EPS历史数据 (mdvaes_eps_history) - 失败")
                    detailed_description.append(f"- 错误原因: {str(e)}")
                    logger.error(f"  ❌ EPS 历史同步失败: {e}")
                detailed_description.append("")
            else:
                detailed_description.append(f"#### ⏭️ EPS历史数据 (mdvaes_eps_history) - 跳过")
                detailed_description.append("")

            # 汇总统计
            success_count = sum(1 for s in table_status.values() if s["status"] == "success")
            error_count = sum(1 for s in table_status.values() if s["status"] == "error")

            detailed_description.append("")
            detailed_description.append("### 汇总统计")
            detailed_description.append(f"- 总计: {total_tables} 张表")
            detailed_description.append(f"- 成功: {success_count} 张")
            detailed_description.append(f"- 失败: {error_count} 张")

            # 构建返回结果（保持向后兼容）
            results = {
                "start_date": start_date,
                "end_date": end_date,
                "selected_tables": tables,
                "summary": {
                    "total": total_tables,
                    "success": success_count,
                    "error": error_count
                },
                "table_status": table_status,
                "detailed_description": "\n".join(detailed_description)
            }

            # 为兼容性，保留原有的数据结构（如果表已同步）
            if "analyst_forecasts" in table_status and table_status["analyst_forecasts"]["status"] == "success":
                results["analyst_forecasts"] = table_status["analyst_forecasts"]["result"]
            if "pe_history" in table_status and table_status["pe_history"]["status"] == "success":
                results["pe_history"] = table_status["pe_history"]["result"]
            if "bond_rate" in table_status and table_status["bond_rate"]["status"] == "success":
                results["bond_rate"] = table_status["bond_rate"]["result"]
            if "financial_ratios" in table_status and table_status["financial_ratios"]["status"] == "success":
                results["financial_ratios"] = table_status["financial_ratios"]["result"]
            if "eps_history" in table_status and table_status["eps_history"]["status"] == "success":
                results["eps_history"] = table_status["eps_history"]["result"]

            logger.info(f"✅ [批量同步] 历史数据同步完成 (成功: {success_count}, 失败: {error_count})")
            return results

        except Exception as e:
            logger.error(f"❌ [批量同步] 历史数据同步失败: {e}", exc_info=True)
            raise

    async def _batch_sync_bond_yield(self, db, start_dt: datetime, end_dt: datetime):
        """批量同步国债收益率

        优化：一次性获取整个时间段的数据
        """
        start_date_str = start_dt.strftime("%Y%m%d")
        end_date_str = end_dt.strftime("%Y%m%d")

        df = await self._call_tushare_with_retry(
            self.pro.yc_cb,
            ts_code="1001.CB",
            curve_type="0",
            curve_term=10.0,
            start_date=start_date_str,
            end_date=end_date_str
        )

        synced = 0  # 新插入的记录数
        updated = 0  # 更新的记录数
        skipped = 0  # 跳过的记录数（数据缺失）

        if not df.empty:
            logger.info(f"📊 开始处理国债收益率数据，共 {len(df)} 条记录")
            for idx, row in df.iterrows():
                record = row.to_dict()
                logger.debug(f"处理记录 {idx+1}/{len(df)}: {list(record.keys())}")

                # 处理日期字段：优先使用 date 字段，其次使用其他可能的字段名
                date_str = record.get("date") or record.get("trade_date") or record.get("cal_date")

                logger.debug(f"日期字段值: date={record.get('date')}, trade_date={record.get('trade_date')}, cal_date={record.get('cal_date')}, date_str={date_str}")

                if not date_str:
                    logger.warning(f"跳过缺少日期字段的记录: {record}")
                    skipped += 1
                    continue

                try:
                    trade_date = datetime.strptime(str(date_str), "%Y%m%d").strftime("%Y%m%d")
                except ValueError as e:
                    logger.error(f"日期解析失败: date_str='{date_str}', record={record}, error={e}")
                    skipped += 1
                    continue

                result = await db.mdvaes_bond_rate.update_one(
                    {
                        "trade_date": trade_date,
                        "curve_term": 10.0
                    },
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

                if result.upserted_id:
                    synced += 1
                else:
                    updated += 1

        # 返回格式：synced=新增, updated=更新, skipped=跳过（兼容前端，将updated计入skipped）
        return {"synced": synced, "updated": updated, "skipped": skipped}

    async def _batch_sync_daily_basic(self, db, start_dt: datetime, end_dt: datetime):
        """批量同步每日估值指标

        注意：由于 Tushare API 的积分限制，start_date/end_date 参数可能只返回最近几天的数据。
        解决方案：逐日调用 API 获取完整的历史数据。
        """
        # 生成日期列表（只包括工作日，避免无用的周末调用）
        date_list = []
        current = start_dt
        while current <= end_dt:
            # 简单的周末检测（周一=0, 周日=6）
            if current.weekday() < 5:  # 0-4 是周一到周五
                date_list.append(current.strftime("%Y%m%d"))
            current = current + timedelta(days=1)

        logger.info(f"  📅 计划同步 {len(date_list)} 个工作日")

        synced = 0  # 新插入的记录数
        updated = 0  # 更新的记录数
        skipped_dates = 0  # 跳过的日期数（无数据）

        # 逐日获取数据
        for idx, trade_date in enumerate(date_list, 1):
            logger.info(f"  📡 [{idx}/{len(date_list)}] 获取 {trade_date} 的数据...")

            df = await self._call_tushare_with_retry(
                self.pro.daily_basic,
                ts_code="",
                trade_date=trade_date,
                fields="ts_code,trade_date,pe,pe_ttm,pb,ps",
                api_name="daily_basic"
            )

            if df.empty:
                logger.warning(f"    ⚠️ {trade_date} 无数据（可能是节假日或停牌）")
                skipped_dates += 1
                continue

            logger.info(f"    📊 {trade_date} 返回 {len(df)} 条记录")

            # 使用 bulk_write 批量插入
            from pymongo import UpdateOne

            operations = []
            for _, row in df.iterrows():
                record = row.to_dict()

                operations.append(
                    UpdateOne(
                        {
                            "ts_code": record["ts_code"],
                            "trade_date": record["trade_date"]
                        },
                        {
                            "$set": {
                                **record,
                                "synced_at": datetime.now()
                            }
                        },
                        upsert=True
                    )
                )

            # 分批执行（每 1000 条）
            batch_size = 1000
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                result = await db.mdvaes_pe_history.bulk_write(batch, ordered=False)
                synced += result.upserted_count
                updated += result.modified_count

            # 每日存储完成后打印日志
            logger.info(f"    ✅ {trade_date}: 新增 {result.upserted_count} 条, 更新 {result.modified_count} 条")

        logger.info(f"  ✅ PE历史同步完成: 新增 {synced} 条, 更新 {updated} 条, 跳过 {skipped_dates} 个日期")

        # 返回格式：synced=新增, updated=更新, skipped=跳过的日期数
        return {"synced": synced, "updated": updated, "skipped": skipped_dates}

    async def _batch_sync_analyst_forecasts(
        self, db, start_dt: datetime, end_dt: datetime,
        job_id: str, total_steps: int, base_step: int
    ):
        """批量同步分析师盈利预测

        重要说明：
        - report_rc 接口返回的是分析师盈利预测研报
        - report_date：研报发布日期（YYYYMMDD 格式）
        - org_name：机构名称

        策略：
        - 使用 report_date 字段获取指定日期范围内发布的研报
        - 起始日期往前推 120 天，以确保获取到该期间开始前发布的预测
        - 唯一标识：ts_code + report_date + org_name（区分不同机构的报告）
        """
        synced = 0  # 新插入的记录数
        updated = 0  # 更新的记录数
        skipped = 0  # 跳过的记录数

        # 起始日期往前推 120 天（约4个月）
        start_dt_adjusted = start_dt - timedelta(days=120)
        start_date_str = start_dt_adjusted.strftime("%Y%m%d")
        end_date_str = end_dt.strftime("%Y%m%d")

        logger.info(f"  📅 用户选择日期范围: {start_dt.strftime('%Y-%m-%d')} 至 {end_dt.strftime('%Y-%m-%d')}")
        logger.info(f"  📅 实际获取研报发布日期范围: {start_date_str} 至 {end_date_str} (往前推120天)")

        # 更新进度
        if job_id:
            await self._update_progress(
                job_id, base_step, total_steps * 3,
                f"正在同步分析师预测: {start_date_str} 至 {end_date_str}"
            )

        # 获取指定日期范围内发布的所有报告
        all_forecasts = []
        offset = 0
        limit = 3000
        page = 1

        while True:
            logger.info(f"  📡 [第{page}页] 获取数据 (offset={offset})...")

            # 使用带重试机制的 Tushare API 调用
            df = await self._call_tushare_with_retry(
                self.pro.report_rc,
                start_date=start_date_str,
                end_date=end_date_str,
                offset=offset,
                limit=limit
            )

            if df.empty:
                logger.info(f"    ⚠️ 第{page}页无数据，停止获取")
                break

            logger.info(f"    📊 第{page}页返回 {len(df)} 条记录")

            # 打印样本数据
            for idx in range(min(2, len(df))):
                sample = df.iloc[idx].to_dict()
                logger.info(f"    样本 {idx+1}: ts_code={sample.get('ts_code')}, org_name={sample.get('org_name')}, report_date={sample.get('report_date')}")

            all_forecasts.append(df)
            offset += limit

            if len(df) < limit:
                logger.info(f"    ✅ 已获取全部数据")
                break

            page += 1

        # 合并所有数据
        if not all_forecasts:
            logger.warning(f"  ⚠️ 指定日期范围内无分析师预测报告")
            return {"synced": 0, "updated": 0, "skipped": 0}

        import pandas as pd
        df_all = pd.concat(all_forecasts, ignore_index=True)
        logger.info(f"  📊 总共获取 {len(df_all)} 条记录")

        # 处理每条记录
        for idx, (_, row) in enumerate(df_all.iterrows()):
            record = row.to_dict()

            # 验证必填字段
            if "ts_code" not in record or "report_date" not in record:
                logger.warning(f"    ⚠️ 记录 {idx+1} 缺少必填字段 (ts_code, report_date): {list(record.keys())}")
                skipped += 1
                continue

            # 构建唯一标识查询条件
            query_filter = {
                "ts_code": record["ts_code"],
                "report_date": record["report_date"]
            }
            # 如果有 org_name，也加入查询条件以区分不同机构的报告
            if "org_name" in record and record["org_name"]:
                query_filter["org_name"] = record["org_name"]

            # 执行 upsert
            try:
                result = await db.mdvaes_analyst_forecasts.update_one(
                    query_filter,
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

                if result.upserted_id:
                    synced += 1
                    if synced % 100 == 0:
                        logger.info(f"    进度: 新增 {synced} 条, 更新 {updated} 条")
                else:
                    updated += 1

            except Exception as e:
                logger.error(f"    ❌ 存储记录 {idx+1} 失败: {e}, record={record}")
                skipped += 1

        logger.info(f"  ✅ 分析师预测同步完成: 新增 {synced} 条, 更新 {updated} 条, 跳过 {skipped} 条")

        # 返回格式：synced=新增, updated=更新, skipped=跳过
        return {"synced": synced, "updated": updated, "skipped": skipped}

    async def _update_progress(self, job_id: str, progress: int, total_items: int, message: str):
        """更新任务进度

        Args:
            job_id: 任务ID
            progress: 当前进度（已完成项数）
            total_items: 总项数
            message: 进度消息
        """
        try:
            from app.core.database import get_mongo_db
            from datetime import datetime as dt

            db = get_mongo_db()
            progress_percent = int((progress / total_items) * 100) if total_items > 0 else 100

            await db.scheduler_executions.update_one(
                {"job_id": job_id, "status": "running"},
                {
                    "$set": {
                        "progress": progress_percent,
                        "progress_message": message,
                        "updated_at": dt.now()
                    }
                }
            )
        except Exception as e:
            logger.warning(f"更新进度失败: {e}")

    async def _sync_financial_ratios(self, db, trade_date: str):
        """同步财务比率数据

        注意：财务数据是季度/年度发布的，不是每日更新。
        每日同步只检查是否需要更新，实际数据通过批量同步获取。
        """
        logger.debug(f"  📊 跳过财务比率每日同步: {trade_date}（财务数据非每日更新）")
        # 财务数据不是每日更新的，跳过每日同步
        # 使用批量同步来获取历史财务数据
        return

    async def _sync_eps_history(self, db, trade_date: str):
        """同步 EPS 历史数据

        注意：EPS 数据是季度/年度发布的，不是每日更新。
        每日同步只检查是否需要更新，实际数据通过批量同步获取。
        """
        logger.debug(f"  📊 跳过 EPS 历史每日同步: {trade_date}（EPS 数据非每日更新）")
        # EPS 数据不是每日更新的，跳过每日同步
        # 使用批量同步来获取历史 EPS 数据
        return

    async def _batch_sync_financial_ratios(self, db, start_dt: datetime, end_dt: datetime):
        """批量同步财务比率数据

        策略：
        1. 先获取股票列表
        2. 分批查询（每次100只股票）避免 API 限制
        3. 使用 start_date/end_date 参数获取日期范围内的数据
        """
        synced = 0  # 新插入的记录数
        updated = 0  # 更新的记录数
        skipped = 0  # 跳过的年份数（无数据）

        # 1. 获取股票列表
        logger.info("  📋 获取股票列表...")
        stock_df = await self._call_tushare_with_retry(
            self.pro.stock_basic,
            list_status='L',
            fields='ts_code,symbol,name',
            api_name="stock_basic"
        )

        if stock_df.empty:
            logger.error("  ❌ 无法获取股票列表")
            return {"synced": 0, "updated": 0, "skipped": 0}

        stock_codes = stock_df['ts_code'].tolist()
        logger.info(f"  ✅ 获取到 {len(stock_codes)} 只股票")

        # 2. 生成年份列表
        years = []
        current = start_dt
        while current.year <= end_dt.year:
            years.append(current.year)
            current = current.replace(year=current.year + 1, month=1, day=1)

        logger.info(f"  📅 计划同步 {len(years)} 个年份的财务比率数据")

        # 3. 按年份和股票批次同步
        # 注意：Tushare fina_indicator 接口有约 100 条记录的返回限制
        # 批量大小设为 20 以确保所有股票数据都能被返回
        batch_size = 20  # 每次查询20只股票

        for year in years:
            year_start = f"{year}0101"
            year_end = f"{year}1231"
            logger.info(f"  📡 获取 {year} 年的财务比率数据...")

            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i + batch_size]
                ts_codes_str = ",".join(batch_codes)

                try:
                    df = await self._call_tushare_with_retry(
                        self.pro.fina_indicator,
                        ts_code=ts_codes_str,
                        start_date=year_start,
                        end_date=year_end,
                        fields="ts_code,ann_date,end_date,debt_to_assets,current_ratio,quick_ratio,roe,roa,bps",
                        api_name="fina_indicator"
                    )

                    if df.empty:
                        logger.warning(f"    ⚠️ {year} 年 批次 {i//batch_size + 1}: 返回空数据（{len(batch_codes)} 只股票）")
                        continue

                    # 检查数据完整性：验证本批次所有股票都有数据
                    unique_stocks_in_df = df['ts_code'].unique()
                    missing_stocks = set(batch_codes) - set(unique_stocks_in_df)
                    if missing_stocks:
                        logger.warning(f"    ⚠️ {year} 年 批次 {i//batch_size + 1}: {len(missing_stocks)} 只股票无数据: {list(missing_stocks)[:5]}{'...' if len(missing_stocks) > 5 else ''}")

                    logger.info(f"    📊 {year} 年 批次 {i//batch_size + 1}: 返回 {len(df)} 条记录，覆盖 {len(unique_stocks_in_df)}/{len(batch_codes)} 只股票")

                    from pymongo import UpdateOne
                    operations = []
                    for _, row in df.iterrows():
                        record = row.to_dict()
                        # 过滤掉 NaN 值，保留所需字段
                        filtered_record = {k: v for k, v in record.items()
                                         if pd.notna(v) and k in ['ts_code', 'ann_date', 'end_date',
                                                                   'debt_to_assets', 'current_ratio',
                                                                   'quick_ratio', 'roe', 'roa', 'bps']}
                        if 'ts_code' in filtered_record and 'end_date' in filtered_record:
                            operations.append(
                                UpdateOne(
                                    {"ts_code": filtered_record["ts_code"], "end_date": filtered_record["end_date"]},
                                    {"$set": {**filtered_record, "synced_at": datetime.now()}},
                                    upsert=True
                                )
                            )

                    if operations:
                        result = await db.mdvaes_financial_ratios.bulk_write(operations, ordered=False)
                        synced += result.upserted_count
                        updated += result.modified_count
                        logger.info(f"    ✅ 新增 {result.upserted_count} 条, 更新 {result.modified_count} 条")

                except Exception as e:
                    logger.error(f"    ❌ {year} 年 批次 {i//batch_size + 1} 同步失败: {e}")
                    skipped += 1

        logger.info(f"  ✅ 财务比率同步完成: 新增 {synced} 条, 更新 {updated} 条, 跳过 {skipped} 个批次")
        return {"synced": synced, "updated": updated, "skipped": skipped}

    async def _batch_sync_eps_history(self, db, start_dt: datetime, end_dt: datetime):
        """批量同步 EPS 历史数据

        策略：
        1. 先获取股票列表
        2. 分批查询（每次100只股票）避免 API 限制
        3. 使用 start_date/end_date 参数获取日期范围内的数据
        """
        synced = 0
        updated = 0
        skipped = 0

        # 1. 获取股票列表
        logger.info("  📋 获取股票列表...")
        stock_df = await self._call_tushare_with_retry(
            self.pro.stock_basic,
            list_status='L',
            fields='ts_code,symbol,name',
            api_name="stock_basic"
        )

        if stock_df.empty:
            logger.error("  ❌ 无法获取股票列表")
            return {"synced": 0, "updated": 0, "skipped": 0}

        stock_codes = stock_df['ts_code'].tolist()
        logger.info(f"  ✅ 获取到 {len(stock_codes)} 只股票")

        # 2. 生成年份列表
        years = []
        current = start_dt
        while current.year <= end_dt.year:
            years.append(current.year)
            current = current.replace(year=current.year + 1, month=1, day=1)

        logger.info(f"  📅 计划同步 {len(years)} 个年份的 EPS 历史数据")

        # 3. 按年份和股票批次同步
        # 注意：Tushare fina_indicator 接口有约 100 条记录的返回限制
        # 批量大小设为 20 以确保所有股票数据都能被返回
        batch_size = 20  # 每次查询20只股票

        for year in years:
            year_start = f"{year}0101"
            year_end = f"{year}1231"
            logger.info(f"  📡 获取 {year} 年的 EPS 数据...")

            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i + batch_size]
                ts_codes_str = ",".join(batch_codes)

                try:
                    df = await self._call_tushare_with_retry(
                        self.pro.fina_indicator,
                        ts_code=ts_codes_str,
                        start_date=year_start,
                        end_date=year_end,
                        fields="ts_code,ann_date,end_date,eps,dt_eps,fcfe_ps,cfps",
                        api_name="fina_indicator"
                    )

                    if df.empty:
                        logger.warning(f"    ⚠️ {year} 年 批次 {i//batch_size + 1}: 返回空数据（{len(batch_codes)} 只股票）")
                        continue

                    # 检查数据完整性：验证本批次所有股票都有数据
                    unique_stocks_in_df = df['ts_code'].unique()
                    missing_stocks = set(batch_codes) - set(unique_stocks_in_df)
                    if missing_stocks:
                        logger.warning(f"    ⚠️ {year} 年 批次 {i//batch_size + 1}: {len(missing_stocks)} 只股票无数据: {list(missing_stocks)[:5]}{'...' if len(missing_stocks) > 5 else ''}")

                    logger.info(f"    📊 {year} 年 批次 {i//batch_size + 1}: 返回 {len(df)} 条记录，覆盖 {len(unique_stocks_in_df)}/{len(batch_codes)} 只股票")

                    from pymongo import UpdateOne
                    operations = []
                    for _, row in df.iterrows():
                        record = row.to_dict()
                        # 字段映射：Tushare 的 fcfe_ps 映射为数据库的 fcfps
                        if 'fcfe_ps' in record and pd.notna(record['fcfe_ps']):
                            record['fcfps'] = record.pop('fcfe_ps')
                        # 过滤掉 NaN 值
                        filtered_record = {k: v for k, v in record.items()
                                         if pd.notna(v) and k in ['ts_code', 'ann_date', 'end_date', 'eps', 'dt_eps', 'fcfps', 'cfps']}
                        if 'ts_code' in filtered_record and 'end_date' in filtered_record:
                            operations.append(
                                UpdateOne(
                                    {"ts_code": filtered_record["ts_code"], "end_date": filtered_record["end_date"]},
                                    {"$set": {**filtered_record, "synced_at": datetime.now()}},
                                    upsert=True
                                )
                            )

                    if operations:
                        result = await db.mdvaes_eps_history.bulk_write(operations, ordered=False)
                        synced += result.upserted_count
                        updated += result.modified_count
                        logger.info(f"    ✅ 新增 {result.upserted_count} 条, 更新 {result.modified_count} 条")

                except Exception as e:
                    logger.error(f"    ❌ {year} 年 批次 {i//batch_size + 1} 同步失败: {e}")
                    skipped += 1

        logger.info(f"  ✅ EPS 历史同步完成: 新增 {synced} 条, 更新 {updated} 条, 跳过 {skipped} 个批次")
        return {"synced": synced, "updated": updated, "skipped": skipped}


# 全局服务实例
_mdvaes_sync_service: Optional[MDVAESDataSyncService] = None


def get_mdvaes_sync_service() -> MDVAESDataSyncService:
    """获取 MDVAES 数据同步服务实例"""
    global _mdvaes_sync_service
    if _mdvaes_sync_service is None:
        _mdvaes_sync_service = MDVAESDataSyncService()
    return _mdvaes_sync_service


# APScheduler 兼容的任务函数
async def run_mdvaes_sync():
    """APScheduler 任务：同步 MDVAES 估值数据（分析师预测、PE/PB、国债收益率）"""
    logger.info("🚀 [APScheduler] 开始执行 MDVAES 数据同步任务")
    try:
        from app.services.trading_calendar_service import get_trading_calendar_service

        # 获取最新交易日
        calendar_service = get_trading_calendar_service()
        latest_trade_date = await calendar_service.get_latest_trading_day()
        trade_date_str = latest_trade_date.strftime("%Y%m%d")

        logger.info(f"📅 [MDVAES] 使用最新交易日: {trade_date_str}")

        # 执行同步
        service = get_mdvaes_sync_service()
        result = await service.sync_daily_data(trade_date_str)

        logger.info(f"✅ [APScheduler] MDVAES 数据同步完成: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ [APScheduler] MDVAES 数据同步失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise


async def run_mdvaes_status_check():
    """APScheduler 任务：检查 MDVAES 数据同步状态"""
    try:
        service = get_mdvaes_sync_service()
        result = await service.get_sync_status()
        logger.info(f"✅ [MDVAES] 状态检查完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ [MDVAES] 状态检查失败: {e}")
        return {"error": str(e)}
