#!/usr/bin/env python3
"""
修复 system_configs 集合中的 is_active 状态

问题：save_system_config 方法没有显式设置 is_active=True，
导致保存的新配置都是 is_active=False，无法被 get_system_config 查询到。

解决方案：将最新版本的配置设为 is_active=True
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def fix_is_active():
    """修复 is_active 状态"""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import settings

    print("🔧 开始修复 system_configs 的 is_active 状态...")

    # 连接数据库
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    config_collection = db.system_configs

    # 1. 查询所有配置，按版本降序
    configs = await config_collection.find().sort("version", -1).to_list(None)
    print(f"📊 找到 {len(configs)} 个配置")

    if not configs:
        print("⚠️  数据库中没有配置")
        return

    # 2. 将所有配置设为非激活
    result = await config_collection.update_many(
        {},
        {"$set": {"is_active": False}}
    )
    print(f"📝 禁用所有配置: {result.modified_count} 条")

    # 3. 将最新版本的配置设为激活
    latest_config = configs[0]
    result = await config_collection.update_one(
        {"_id": latest_config["_id"]},
        {"$set": {"is_active": True}}
    )
    print(f"✅ 激活最新配置 (版本 {latest_config.get('version', 0)}): {result.modified_count} 条")

    # 4. 验证修复结果
    active_config = await config_collection.find_one({"is_active": True})
    if active_config:
        print(f"✅ 修复成功！激活的配置版本: {active_config.get('version', 0)}")
        print(f"   LLM配置数量: {len(active_config.get('llm_configs', []))}")
        print(f"   数据源配置数量: {len(active_config.get('data_source_configs', []))}")
    else:
        print("❌ 修复失败！没有找到激活的配置")

    await client.close()


if __name__ == "__main__":
    asyncio.run(fix_is_active())
