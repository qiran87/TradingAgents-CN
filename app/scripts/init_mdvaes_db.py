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
        await db.mdvaes_analyst_forecasts.create_index([
            ("ts_code", 1),
            ("quarter", 1),
            ("report_date", -1)
        ])
        print("✅ mdvaes_analyst_forecasts 索引创建完成")

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
