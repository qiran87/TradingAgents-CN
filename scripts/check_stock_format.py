#!/usr/bin/env python3
"""检查数据库中的股票代码格式"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymongo
from app.core.config import settings

def check_format():
    client = pymongo.MongoClient(
        settings.MONGODB_HOST,
        settings.MONGODB_PORT,
        username=settings.MONGODB_USERNAME,
        password=settings.MONGODB_PASSWORD,
        authSource=settings.MONGODB_AUTH_SOURCE
    )
    db = client[settings.MONGODB_DATABASE]

    # 检查 stock_daily_quotes 表的格式
    print("=== stock_daily_quotes 表 ===")
    samples = list(db.stock_daily_quotes.find({'ts_code': {'$exists': True}}).limit(20))
    if samples:
        unique_codes = sorted(set(s['ts_code'] for s in samples))
        print(f"样本代码: {unique_codes[:20]}")
    else:
        print("没有数据")

    # 统计 .SH 和 .SS 的数量
    sh_count = db.stock_daily_quotes.count_documents({'ts_code': {'$regex': r'\.SH$'}})
    ss_count = db.stock_daily_quotes.count_documents({'ts_code': {'$regex': r'\.SS$'}})
    sz_count = db.stock_daily_quotes.count_documents({'ts_code': {'$regex': r'\.SZ$'}})

    print(f".SH 格式数量: {sh_count}")
    print(f".SS 格式数量: {ss_count}")
    print(f".SZ 格式数量: {sz_count}")

    # 检查 mdvaes_pe_history 表的格式
    print("\n=== mdvaes_pe_history 表 ===")
    pe_samples = list(db.mdvaes_pe_history.find({'ts_code': {'$exists': True}}).limit(20))
    if pe_samples:
        pe_unique_codes = sorted(set(s['ts_code'] for s in pe_samples))
        print(f"样本代码: {pe_unique_codes[:20]}")
    else:
        print("没有数据")

    pe_sh_count = db.mdvaes_pe_history.count_documents({'ts_code': {'$regex': r'\.SH$'}})
    pe_ss_count = db.mdvaes_pe_history.count_documents({'ts_code': {'$regex': r'\.SS$'}})
    pe_sz_count = db.mdvaes_pe_history.count_documents({'ts_code': {'$regex': r'\.SZ$'}})

    print(f".SH 格式数量: {pe_sh_count}")
    print(f".SS 格式数量: {pe_ss_count}")
    print(f".SZ 格式数量: {pe_sz_count}")

    # 检查 600519 的数据
    print("\n=== 600519 股票的数据 ===")
    for table in ['stock_daily_quotes', 'mdvaes_pe_history', 'mdvaes_eps_history']:
        samples = list(db[table].find({'ts_code': {'$regex': '600519'}}).limit(5))
        print(f"{table}:")
        for s in samples:
            print(f"  ts_code: {s.get('ts_code')}, trade_date: {s.get('trade_date')}")
        if not samples:
            print(f"  无数据")

if __name__ == "__main__":
    check_format()
