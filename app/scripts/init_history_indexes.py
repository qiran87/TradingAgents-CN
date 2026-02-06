"""
回测历史记录数据库索引初始化脚本

创建 backtest_history 集合的索引
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_history_indexes():
    """初始化回测历史记录相关索引"""
    logger.info("🔧 开始创建回测历史记录相关索引...")

    # 连接MongoDB
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGODB_DATABASE]

    # 定义索引
    indexes = [
        {
            "collection": "backtest_history",
            "indexes": [
                {
                    "keys": [("record_id", 1)],
                    "options": {"unique": True, "name": "record_id_unique"}
                },
                {
                    "keys": [("user_id", 1), ("created_at", -1)],
                    "options": {"name": "user_id_created_at_idx"}
                },
                {
                    "keys": [("parameters.strategy_id", 1)],
                    "options": {"name": "strategy_id_idx"}
                },
                {
                    "keys": [("parameters.stock_code", 1)],
                    "options": {"name": "stock_code_idx"}
                },
                {
                    "keys": [("name", "text"), ("description", "text")],
                    "options": {"name": "text_search_idx"}
                }
            ]
        }
    ]

    # 创建索引
    for index_config in indexes:
        collection_name = index_config["collection"]
        logger.info(f"📊 处理 {collection_name} 索引...")

        try:
            collection = db[collection_name]

            for idx in index_config["indexes"]:
                index_name = idx["options"]["name"]
                keys = idx["keys"]
                options = idx["options"]

                try:
                    # 尝试删除旧索引
                    await collection.drop_index(index_name)
                    logger.info(f"🗑️  已删除旧的 {index_name} 索引")
                except Exception:
                    # 索引不存在，忽略
                    pass

                # 创建新索引
                await collection.create_index(keys, **{k: v for k, v in options.items() if k != "name"})
                logger.info(f"✅ {collection_name}.{index_name} 索引创建完成")

        except Exception as e:
            logger.warning(f"⚠️  {collection_name} 索引处理失败: {e}")
            logger.info(f"ℹ️  跳过 {collection_name} 索引，继续处理其他集合")

    logger.info("✅ 数据库索引创建完成")
    client.close()


if __name__ == "__main__":
    asyncio.run(init_history_indexes())
