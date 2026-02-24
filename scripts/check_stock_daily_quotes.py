#!/usr/bin/env python3
"""检查 stock_daily_quotes 表的状态"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
import pymongo

def check_table():
    client = pymongo.MongoClient(
        settings.MONGODB_HOST,
        settings.MONGODB_PORT,
        username=settings.MONGODB_USERNAME,
        password=settings.MONGODB_PASSWORD,
        authSource=settings.MONGODB_AUTH_SOURCE
    )
    db = client[settings.MONGODB_DATABASE]

    print("=== 检查 stock_daily_quotes 表 ===")

    # 1. 检查表是否存在
    collections = db.list_collection_names()
    if 'stock_daily_quotes' not in collections:
        print("❌ stock_daily_quotes 表不存在！")
        return

    print("✅ stock_daily_quotes 表存在")

    # 2. 检查数据量
    total_count = db.stock_daily_quotes.estimated_document_count()
    print(f"📊 总记录数: {total_count:,}")

    # 3. 检查 600519 的数据
    sh_count = db.stock_daily_quotes.count_documents({"ts_code": {"$regex": "600519"}})
    ss_count = db.stock_daily_quotes.count_documents({"ts_code": {"$regex": r"\.SH$|\.SS$"}})
    print(f"📊 600519 相关记录数: {sh_count:,}")
    print(f"📊 .SH/.SS 后缀记录数: {ss_count:,}")

    # 4. 检查索引
    print("\n=== 索引信息 ===")
    indexes = db.stock_daily_quotes.list_indexes()
    for idx in indexes:
        print(f"  索引: {idx['name']}")
        print(f"    键: {idx['key']}")

    # 5. 检查 600519.SH 的样本数据
    print("\n=== 600519.SH 样本数据 ===")
    samples = list(db.stock_daily_quotes.find({"ts_code": "600519.SH"}).limit(3))
    if samples:
        for s in samples:
            print(f"  {s.get('trade_date')}: close={s.get('close')}")
    else:
        print("  无数据")

    # 6. 测试查询速度
    print("\n=== 测试查询速度 ===")
    import time

    # 测试聚合管道查询
    start = time.time()
    pipeline = [
        {"$match": {"ts_code": "600519.SH", "trade_date": {"$lt": "20240102"}}},
        {"$sort": {"trade_date": -1}},
        {"$limit": 1}
    ]
    try:
        result = list(db.stock_daily_quotes.aggregate(pipeline, maxTimeMS=5000))
        elapsed = time.time() - start
        print(f"  聚合管道查询: {elapsed:.2f} 秒")
        if result:
            print(f"    结果: {result[0]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  聚合管道查询: {elapsed:.2f} 秒 (超时/失败)")
        print(f"    错误: {e}")

    # 测试简单 find_one 查询
    start = time.time()
    try:
        result = db.stock_daily_quotes.find_one(
            {"ts_code": "600519.SH", "trade_date": {"$lt": "20240102"}},
            sort=[("trade_date", -1)],
            max_time_ms=5000
        )
        elapsed = time.time() - start
        print(f"  find_one 查询: {elapsed:.2f} 秒")
        if result:
            print(f"    结果: close={result.get('close')}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  find_one 查询: {elapsed:.2f} 秒 (失败)")
        print(f"    错误: {e}")

if __name__ == "__main__":
    check_table()
