"""
初始化回测结果相关数据库索引

运行方式：
    python -m app.scripts.init_result_indexes
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_indexes():
    """创建回测结果相关集合的索引"""
    try:
        # 连接MongoDB（使用完整的URI，包含认证信息）
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.MONGODB_DATABASE]

        logger.info("🔧 开始创建回测结果相关索引...")

        # backtest_results 集合索引（先删除后创建，避免冲突）
        try:
            logger.info("📊 处理 backtest_results 索引...")
            # 尝试删除旧索引（如果存在）
            try:
                await db.backtest_results.drop_index("backtest_id_unique")
                logger.info("🗑️  已删除旧的 backtest_id_unique 索引")
            except Exception:
                # 索引不存在，忽略错误
                pass

            # 创建新索引
            await db.backtest_results.create_index(
                [("backtest_id", 1)],
                unique=True,
                name="backtest_id_unique"
            )
            logger.info("✅ backtest_results.backtest_id 唯一索引创建完成")
        except Exception as e:
            logger.warning(f"⚠️  backtest_results 索引处理失败: {e}")
            logger.info("ℹ️  跳过 backtest_results 索引，继续处理其他集合")

        # backtest_tasks 集合索引（先删除后创建，避免冲突）
        try:
            logger.info("📊 处理 backtest_tasks 索引...")
            try:
                await db.backtest_tasks.drop_index("backtest_id_unique")
                logger.info("🗑️  已删除旧的 backtest_id_unique 索引")
            except Exception:
                pass

            await db.backtest_tasks.create_index(
                [("backtest_id", 1)],
                unique=True,
                name="backtest_id_unique"
            )
            logger.info("✅ backtest_tasks.backtest_id 唯一索引创建完成")
        except Exception as e:
            logger.warning(f"⚠️  backtest_tasks 索引处理失败: {e}")
            logger.info("ℹ️  跳过 backtest_tasks 索引，继续处理其他集合")

        # backtest_trades 集合索引
        try:
            logger.info("📊 处理 backtest_trades 索引...")
            try:
                await db.backtest_trades.drop_index("backtest_id_date_index")
                logger.info("🗑️  已删除旧的 backtest_id_date_index 索引")
            except Exception:
                pass

            await db.backtest_trades.create_index(
                [("backtest_id", 1), ("date", 1)],
                name="backtest_id_date_index"
            )
            logger.info("✅ backtest_trades.backtest_id_date 复合索引创建完成")
        except Exception as e:
            logger.warning(f"⚠️  backtest_trades 索引处理失败: {e}")
            logger.info("ℹ️  跳过 backtest_trades 索引，继续处理其他集合")

        # backtest_daily_states 集合索引
        try:
            logger.info("📊 处理 backtest_daily_states 索引...")
            try:
                await db.backtest_daily_states.drop_index("backtest_id_bar_index_index")
                logger.info("🗑️  已删除旧的 backtest_id_bar_index_index 索引")
            except Exception:
                pass

            await db.backtest_daily_states.create_index(
                [("backtest_id", 1), ("bar_index", 1)],
                name="backtest_id_bar_index_index"
            )
            logger.info("✅ backtest_daily_states.backtest_id_bar_index 复合索引创建完成")
        except Exception as e:
            logger.warning(f"⚠️  backtest_daily_states 索引处理失败: {e}")
            logger.info("ℹ️  跳过 backtest_daily_states 索引，继续处理其他集合")

        logger.info("✅ 数据库索引创建完成")

        # 关闭连接
        client.close()

    except Exception as e:
        logger.error(f"❌ 创建索引失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(create_indexes())
