"""初始化 MDVAES 相关的 MongoDB 集合和索引"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def create_mdvaes_collections():
    """创建 MDVAES 集合和索引"""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    try:
        # 1. 分析师盈利预测
        # 先删除旧索引，避免冲突
        existing_indexes = await db.mdvaes_analyst_forecasts.list_indexes().to_list(None)
        for idx in existing_indexes:
            idx_name = idx.get("name")
            if idx_name != "_id_":  # 保留默认的 _id 索引
                await db.mdvaes_analyst_forecasts.drop_index(idx_name)
                print(f"  🗑️ 删除旧索引: {idx_name}")

        # 清理重复数据（保留最新的记录）
        print("  🧹 清理重复数据...")
        duplicate_count = 0
        async for doc in db.mdvaes_analyst_forecasts.find().sort("synced_at", -1):
            # 检查是否有相同 ts_code + report_date + org_name 的记录
            query = {
                "ts_code": doc["ts_code"],
                "report_date": doc["report_date"],
                "_id": {"$ne": doc["_id"]}  # 排除当前记录
            }
            if "org_name" in doc and doc["org_name"]:
                query["org_name"] = doc["org_name"]

            # 删除重复的旧记录
            result = await db.mdvaes_analyst_forecasts.delete_many(query)
            if result.deleted_count > 0:
                duplicate_count += result.deleted_count

        if duplicate_count > 0:
            print(f"  ✅ 已删除 {duplicate_count} 条重复记录")
        else:
            print(f"  ℹ️ 没有发现重复数据")

        # 创建新的唯一索引: ts_code + report_date + org_name
        await db.mdvaes_analyst_forecasts.create_index([
            ("ts_code", 1),
            ("report_date", 1),
            ("org_name", 1)
        ], unique=True, sparse=True)  # sparse=True 允许 org_name 为空的记录
        print("✅ mdvaes_analyst_forecasts 索引创建完成 (ts_code + report_date + org_name)")

        # 2. EPS 历史数据
        await db.mdvaes_eps_history.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_eps_history 索引创建完成")

        # 3. PE 历史数据
        await db.mdvaes_pe_history.create_index([
            ("ts_code", 1),
            ("trade_date", -1)
        ])
        print("✅ mdvaes_pe_history 索引创建完成")

        # 4. 现金流数据
        await db.mdvaes_cashflow_data.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_cashflow_data 索引创建完成")

        # 5. 财务比率
        await db.mdvaes_financial_ratios.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_financial_ratios 索引创建完成")

        # 6. 国债收益率
        await db.mdvaes_bond_rate.create_index([
            ("trade_date", -1),
            ("curve_term", 1)
        ])
        print("✅ mdvaes_bond_rate 索引创建完成")

        # 7. 估值缓存
        await db.mdvaes_valuation_cache.create_index([
            ("ts_code", 1),
            ("calculation_date", -1),
            ("params_hash", 1)
        ])
        print("✅ mdvaes_valuation_cache 索引创建完成")

        print("\n🎉 所有 MDVAES 集合和索引创建完成！")

    except Exception as e:
        print(f"❌ 创建索引失败: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(create_mdvaes_collections())
