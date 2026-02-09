#!/usr/bin/env python3
"""检查数据库所有集合的结构"""
import motor.motor_asyncio
import asyncio
import json

MONGO_URI = 'mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin'

async def check_all_collections():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client.tradingagents

    # 获取所有集合
    collections = await db.list_collection_names()

    print("=" * 80)
    print(f"数据库中共有 {len(collections)} 个集合")
    print("=" * 80)

    # 存储集合结构信息
    db_structure = {}

    for col_name in sorted(collections):
        print(f"\n检查集合: {col_name}")

        # 获取样本文档
        sample = await db[col_name].find_one({})

        if sample:
            # 提取字段信息
            fields = set()

            def extract_fields(doc, prefix=''):
                for key, value in doc.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    fields.add(full_key)
                    if isinstance(value, dict):
                        extract_fields(value, full_key)
                    elif isinstance(value, list) and value and isinstance(value[0], dict):
                        # 检查数组中的对象
                        extract_fields(value[0], full_key)

            extract_fields(sample)

            # 统计文档数量
            count = await db[col_name].count_documents({})

            db_structure[col_name] = {
                'count': count,
                'fields': sorted(list(fields)),
                'sample_keys': list(sample.keys()) if sample else []
            }

            print(f"  文档数量: {count}")
            print(f"  字段数量: {len(fields)}")
            main_fields = list(sample.keys())[:15]
            print(f"  主要字段: {', '.join(main_fields)}")
        else:
            print(f"  ⚠️ 集合为空")
            db_structure[col_name] = {'count': 0, 'fields': [], 'sample_keys': []}

    # 保存到文件
    with open('/tmp/db_structure.json', 'w') as f:
        json.dump(db_structure, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print(f"✅ 数据库结构已保存到 /tmp/db_structure.json")
    print("=" * 80)

    client.close()
    return db_structure

if __name__ == "__main__":
    asyncio.run(check_all_collections())
