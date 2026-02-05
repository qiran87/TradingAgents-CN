#!/usr/bin/env python3
"""
回测引擎测试数据准备脚本
在数据库中插入测试用的历史行情数据
"""

import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def prepare_test_data():
    """准备测试数据"""
    load_dotenv()
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    mongo_db = os.getenv('MONGO_DB', 'tradingagents')

    client = AsyncIOMotorClient(mongo_uri)
    db = client[mongo_db]

    stock_code = "000001.SZ"

    # 生成2023年12月1日-5日的测试数据
    test_quotes = []
    dates = ["2023-12-01", "2023-12-04", "2023-12-05"]  # 跳过周末

    base_price = 10.0
    for i, date_str in enumerate(dates):
        price = base_price + (i * 0.1)  # 价格递增
        quote = {
            "stock_code": stock_code,
            "date": date_str,
            "open": round(price, 2),
            "high": round(price * 1.02, 2),
            "low": round(price * 0.98, 2),
            "close": round(price * 1.01, 2),
            "volume": 1000000,
            "amount": 10000000 * price,
            "turnover": 0.1,
            "pct_chg": 1.0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        test_quotes.append(quote)

    # 删除已存在的测试数据
    await db.stock_daily_quotes.delete_many({
        "stock_code": stock_code,
        "date": {"$in": dates}
    })
    logger.info(f"✓ 已删除旧的测试数据")

    # 插入新数据
    await db.stock_daily_quotes.insert_many(test_quotes)
    logger.info(f"✓ 已插入 {len(test_quotes)} 条测试数据")

    # 验证数据
    count = await db.stock_daily_quotes.count_documents({
        "stock_code": stock_code,
        "date": {"$in": dates}
    })
    logger.info(f"✓ 验证：数据库中有 {count} 条 {stock_code} 的测试数据")

    client.close()


if __name__ == "__main__":
    asyncio.run(prepare_test_data())
