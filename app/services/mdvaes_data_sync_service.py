"""MDVAES 数据同步服务 - 从 Tushare 同步数据到 MongoDB"""

import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import tushare as ts
from app.core.config import settings
from app.core.database import get_mongo_db

logger = logging.getLogger(__name__)


class MDVAESDataSyncService:
    """MDVAES 数据同步服务"""

    def __init__(self):
        self.pro = ts.pro_api(settings.TUSHARE_TOKEN)

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
            # 使用 asyncio.to_thread 在单独线程中执行阻塞的 Tushare API 调用
            df = await asyncio.to_thread(
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
                await db.mdvaes_analyst_forecasts.update_one(
                    {
                        "ts_code": record["ts_code"],
                        "quarter": record["quarter"],
                        "report_date": record["report_date"]
                    },
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

        # 使用 asyncio.to_thread 在单独线程中执行阻塞的 Tushare API 调用
        df = await asyncio.to_thread(
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
        # 使用 asyncio.to_thread 在单独线程中执行阻塞的 Tushare API 调用
        df = await asyncio.to_thread(
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
        job_id: str = None
    ):
        """批量同步历史数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            job_id: 任务ID（用于进度报告）

        Returns:
            同步结果统计
        """
        logger.info(f"🚀 [批量同步] 开始同步历史数据: {start_date} 至 {end_date}")

        db = get_mongo_db()
        results = {
            "start_date": start_date,
            "end_date": end_date,
            "analyst_forecasts": {"synced": 0, "skipped": 0},
            "pe_history": {"synced": 0, "skipped": 0},
            "bond_rate": {"synced": 0, "skipped": 0}
        }

        try:
            # 转换日期格式
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # 总天数估算
            total_days = (end_dt - start_dt).days + 1
            current_step = 0

            # 1. 批量同步国债收益率（一次性获取整个时间段）
            logger.info("📊 [批量同步] 开始同步国债收益率...")
            current_step = 1
            if job_id:
                await self._update_progress(job_id, current_step, total_days * 3, "正在同步国债收益率")
            bond_result = await self._batch_sync_bond_yield(db, start_dt, end_dt)
            results["bond_rate"] = bond_result
            logger.info(f"  ✅ 国债收益率同步完成: 新增 {bond_result['synced']} 条")

            # 2. 批量同步每日估值指标（一次性获取整个时间段）
            logger.info("📊 [批量同步] 开始同步每日估值指标...")
            current_step = total_days
            if job_id:
                await self._update_progress(job_id, current_step, total_days * 3, "正在同步每日估值指标")
            pe_result = await self._batch_sync_daily_basic(db, start_dt, end_dt)
            results["pe_history"] = pe_result
            logger.info(f"  ✅ 每日估值指标同步完成: 新增 {pe_result['synced']} 条")

            # 3. 批量同步分析师盈利预测（按报告日期逐个获取）
            logger.info("📊 [批量同步] 开始同步分析师盈利预测...")
            # 分析师预测按报告日期获取，从结束日期倒推获取最近的报告日期
            analyst_result = await self._batch_sync_analyst_forecasts(
                db, start_dt, end_dt, job_id, total_days, current_step
            )
            results["analyst_forecasts"] = analyst_result
            logger.info(f"  ✅ 分析师预测同步完成: 新增 {analyst_result['synced']} 条")

            logger.info(f"✅ [批量同步] 历史数据同步完成")
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

        df = await asyncio.to_thread(
            self.pro.yc_cb,
            ts_code="1001.CB",
            curve_type="0",
            curve_term=10.0,
            start_date=start_date_str,
            end_date=end_date_str
        )

        synced = 0
        skipped = 0

        if not df.empty:
            for _, row in df.iterrows():
                record = row.to_dict()
                # 处理日期字段：优先使用 date 字段，其次使用其他可能的字段名
                date_str = record.get("date") or record.get("trade_date") or record.get("cal_date")
                if not date_str:
                    logger.warning(f"跳过缺少日期字段的记录: {record}")
                    continue

                trade_date = datetime.strptime(str(date_str), "%Y%m%d").strftime("%Y%m%d")

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
                    skipped += 1

        return {"synced": synced, "skipped": skipped}

    async def _batch_sync_daily_basic(self, db, start_dt: datetime, end_dt: datetime):
        """批量同步每日估值指标

        优化：一次性获取整个时间段的数据
        """
        start_date_str = start_dt.strftime("%Y%m%d")
        end_date_str = end_dt.strftime("%Y%m%d")

        df = await asyncio.to_thread(
            self.pro.daily_basic,
            ts_code="",
            start_date=start_date_str,
            end_date=end_date_str,
            fields="ts_code,trade_date,pe,pe_ttm,pb,ps"
        )

        synced = 0
        skipped = 0

        if not df.empty:
            # 使用 bulk_write 批量插入提高性能
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
                skipped += result.modified_count

        return {"synced": synced, "skipped": skipped}

    async def _batch_sync_analyst_forecasts(
        self, db, start_dt: datetime, end_dt: datetime,
        job_id: str, total_steps: int, base_step: int
    ):
        """批量同步分析师盈利预测

        优化：获取指定时间段内的所有报告日期
        注意：分析师预测数据较少，按季度获取
        """
        # 获取该时间段内的所有季度
        quarters = []
        current = end_dt
        while current >= start_dt:
            year = current.year
            quarter = (current.month - 1) // 3 + 1
            quarters.append(f"{year}Q{quarter}")
            current = current.replace(month=1, day=1) - timedelta(days=1)

        # 去重并排序
        quarters = sorted(set(quarters), reverse=True)

        synced = 0
        skipped = 0
        total_quarters = len(quarters)

        for i, quarter in enumerate(quarters):
            # 更新进度
            if job_id:
                progress = int(base_step + (i / total_quarters) * total_steps)
                await self._update_progress(
                    job_id, progress, total_steps * 3,
                    f"正在同步分析师预测: {quarter} ({i+1}/{total_quarters})"
                )

            # 获取该季度的所有报告
            # 注意：Tushare report_rc 接口需要用 period 参数获取季度数据
            df = await asyncio.to_thread(
                self.pro.report_rc,
                period=quarter,
                offset=0,
                limit=5000
            )

            if not df.empty:
                for _, row in df.iterrows():
                    record = row.to_dict()

                    result = await db.mdvaes_analyst_forecasts.update_one(
                        {
                            "ts_code": record["ts_code"],
                            "quarter": record["quarter"],
                            "report_date": record["report_date"]
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
                        skipped += 1

        return {"synced": synced, "skipped": skipped}

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
