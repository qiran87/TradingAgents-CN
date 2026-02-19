"""MDVAES 数据同步 Worker"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.mdvaes_data_sync_service import get_mdvaes_sync_service
from app.services.trading_calendar_service import get_trading_calendar_service

logger = logging.getLogger(__name__)

# 创建调度器
scheduler = AsyncIOScheduler()


async def daily_sync_task():
    """每日数据同步任务（每个交易日 16:30 执行）"""
    try:
        # 获取服务实例
        sync_service = get_mdvaes_sync_service()
        calendar_service = get_trading_calendar_service()

        # 获取最新交易日
        latest_trade_date = await calendar_service.get_latest_trading_day()
        trade_date_str = latest_trade_date.strftime("%Y%m%d")

        # 执行同步
        result = await sync_service.sync_daily_data(trade_date_str)
        logger.info(f"MDVAES 每日同步完成: {result}")

    except Exception as e:
        logger.error(f"MDVAES 每日同步失败: {e}", exc_info=True)


# 配置定时任务
scheduler.add_job(
    daily_sync_task,
    'cron',
    hour=16,
    minute=30,
    id='mdvaes_daily_sync',
    name='MDVAES 每日数据同步'
)


async def main():
    """启动 Worker"""
    logger.info("MDVAES 数据同步 Worker 启动")
    scheduler.start()

    try:
        # 保持运行
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
        scheduler.shutdown()
        logger.info("MDVAES 数据同步 Worker 已停止")


if __name__ == "__main__":
    asyncio.run(main())
