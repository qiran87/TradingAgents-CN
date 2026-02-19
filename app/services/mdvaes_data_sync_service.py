"""MDVAES 数据同步服务 - 从 Tushare 同步数据到 MongoDB"""

import logging
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

        db = await get_mongo_db()

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
            df = self.pro.report_rc(
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

        df = self.pro.daily_basic(
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
        df = self.pro.yc_cb(
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
