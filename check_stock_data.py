#!/usr/bin/env python3
"""检查数据库中的股票数据"""
import motor.motor_asyncio
import asyncio

MONGO_URI = "mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin"

async def check_stock_data():
    """查询股票数据"""
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client.tradingagents

    try:
        # 1. 列出所有集合
        collections = await db.list_collection_names()
        print(f"\n数据库中的集合: {collections}")

        # 2. 查询 stock_daily_quotes 集合
        if 'stock_daily_quotes' in collections:
            print(f"\n✅ stock_daily_quotes 集合存在")

            # 查看样例数据结构
            sample = await db.stock_daily_quotes.find_one({})
            if sample:
                print(f"\n样例数据字段:")
                for key in sorted(sample.keys()):
                    if key != '_id':
                        value = sample[key]
                        print(f"  {key}: {type(value).__name__}")

            # 查询2024年11月数据
            count_nov = await db.stock_daily_quotes.count_documents({
                "trade_date": {"$gte": "2024-11-01", "$lte": "2024-11-30"}
            })
            print(f"\n2024年11月数据: {count_nov} 条")

            # 查询000001.SZ的数据
            count_000001 = await db.stock_daily_quotes.count_documents({
                "symbol": {"$regex": "^000001"},
                "trade_date": {"$gte": "2024-11-01", "$lte": "2024-11-30"}
            })
            print(f"000001.* 在2024年11月: {count_000001} 条")

            # 查询数据日期范围
            first = await db.stock_daily_quotes.find_one(
                {"symbol": {"$regex": "^000001"}},
                sort=[("trade_date", 1)]
            )
            last = await db.stock_daily_quotes.find_one(
                {"symbol": {"$regex": "^000001"}},
                sort=[("trade_date", -1)]
            )
            if first and last:
                print(f"\n000001 数据日期范围: {first.get('trade_date')} 至 {last.get('trade_date')}")

            # 查询总数据量
            total_count = await db.stock_daily_quotes.count_documents({
                "symbol": {"$regex": "^000001"}
            })
            print(f"000001 总数据量: {total_count} 条")

            # 查看前3条数据
            if count_000001 > 0:
                cursor = db.stock_daily_quotes.find({
                    "symbol": {"$regex": "^000001"},
                    "date": {"$gte": "2024-11-01", "$lte": "2024-11-30"}
                }).limit(3)

                print(f"\n前3条数据:")
                async for doc in cursor:
                    doc.pop('_id', None)
                    print(f"  {doc}")
        else:
            print(f"\n❌ stock_daily_quotes 集合不存在")
            print(f"可用的集合: {collections}")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_stock_data())
