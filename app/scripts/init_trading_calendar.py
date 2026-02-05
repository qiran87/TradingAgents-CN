"""
初始化交易日历数据

创建交易日历集合的索引,并生成2020-2025年的交易日历数据
"""
import asyncio
import logging
from datetime import datetime, date

from app.core.database import get_mongo_db, init_db, close_db, get_redis_client

logger = logging.getLogger(__name__)


async def create_trading_calendar_indexes():
    """创建交易日历集合的索引"""
    db = get_mongo_db()
    collection = db.trading_calendar

    try:
        # 日期唯一索引
        await collection.create_index([("date", 1)], unique=True)
        logger.info("✅ 创建日期唯一索引")

        # 年份索引
        await collection.create_index([("year", 1)])
        logger.info("✅ 创建年份索引")

        # 是否交易日索引
        await collection.create_index([("is_trading_day", 1)])
        logger.info("✅ 创建是否交易日索引")

        # 复合索引：年份 + 日期
        await collection.create_index([("year", 1), ("date", 1)])
        logger.info("✅ 创建年份+日期复合索引")

        logger.info("✅ 交易日历索引创建完成")
        return True
    except Exception as e:
        logger.error(f"❌ 创建索引失败: {e}")
        return False


async def generate_trading_calendar_data(start_year: int = 2020, end_year: int = 2025):
    """
    生成交易日历数据(简化版本,仅区分周末)

    注意:这是一个简化版本的交易日历生成器,仅区分周末。
    实际的交易日历需要考虑节假日调休,应该从专业的金融数据源获取。

    Args:
        start_year: 起始年份
        end_year: 结束年份
    """
    db = get_mongo_db()
    collection = db.trading_calendar

    try:
        # 清空现有数据
        await collection.delete_many({})
        logger.info(f"🗑️  清空现有交易日历数据")

        documents = []
        count = 0

        for year in range(start_year, end_year + 1):
            logger.info(f"📅 生成 {year} 年交易日历数据...")

            # 遍历全年每一天
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")

                # 判断是否为周末(周六=5,周日=6)
                weekday = current_date.weekday()  # 0=周一, 6=周日
                is_weekend = weekday >= 5

                # 简化版本:周末不是交易日,工作日是交易日
                # TODO: 实际应用中需要从专业数据源获取节假日信息
                is_trading_day = not is_weekend

                doc = {
                    "date": date_str,
                    "year": year,
                    "month": current_date.month,
                    "day": current_date.day,
                    "weekday": weekday + 1,  # 转换为1-7(1=周一)
                    "is_trading_day": is_trading_day,
                    "is_holiday": False,  # 简化版本不标记节假日
                    "holiday_name": None,
                    "is_weekend": is_weekend,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                documents.append(doc)
                count += 1

                # 批量插入(每1000条)
                if len(documents) >= 1000:
                    await collection.insert_many(documents)
                    logger.info(f"   已插入 {count} 条数据")
                    documents = []

                current_date = current_date.__add__(__import__('datetime').timedelta(days=1))

        # 插入剩余的记录
        if documents:
            await collection.insert_many(documents)

        logger.info(f"✅ 交易日历数据生成完成,共 {count} 条记录")

        # 清除Redis缓存
        redis_client = get_redis_client()
        await clear_trading_calendar_cache(redis_client)

        return count
    except Exception as e:
        logger.error(f"❌ 生成交易日历数据失败: {e}")
        return 0


async def clear_trading_calendar_cache(redis_client):
    """清除交易日历相关的所有缓存"""
    try:
        # 使用SCAN命令避免阻塞
        cursor = 0
        patterns = [
            "trading_day:*",
            "trading_days:*",
            "prev_trading_day:*",
            "next_trading_day:*"
        ]

        for pattern in patterns:
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    await redis_client.delete(*keys)

                if cursor == 0:
                    break

        logger.info("✅ 交易日历缓存已清除")
    except Exception as e:
        logger.warning(f"⚠️  清除缓存失败: {e}")


async def validate_trading_calendar_data():
    """验证交易日历数据的完整性"""
    db = get_mongo_db()
    collection = db.trading_calendar

    try:
        # 统计数据
        total_count = await collection.count_documents({})
        trading_days_count = await collection.count_documents({"is_trading_day": True})
        weekends_count = await collection.count_documents({"is_weekend": True})

        logger.info(f"📊 交易日历数据统计:")
        logger.info(f"   总天数: {total_count}")
        logger.info(f"   交易日: {trading_days_count}")
        logger.info(f"   周末: {weekends_count}")

        # 检查是否有重复日期
        pipeline = [
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = await collection.aggregate(pipeline).to_list(length=100)

        if duplicates:
            logger.warning(f"⚠️  发现 {len(duplicates)} 个重复日期")
            return False
        else:
            logger.info("✅ 无重复日期")

        # 检查缺失日期(抽查2024年)
        year = 2024
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        existing_dates = set()
        cursor = collection.find({"year": year}, projection=["date"])
        async for doc in cursor:
            existing_dates.add(doc["date"])

        missing_count = 0
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in existing_dates:
                missing_count += 1
            current_date = current_date.__add__(__import__('datetime').timedelta(days=1))

        if missing_count > 0:
            logger.warning(f"⚠️  {year}年缺失 {missing_count} 个日期")
            return False
        else:
            logger.info(f"✅ {year}年数据完整")

        logger.info("✅ 交易日历数据验证通过")
        return True
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False


async def init_trading_calendar():
    """初始化交易日历"""
    logger.info("=" * 70)
    logger.info("📅 开始初始化交易日历...")
    logger.info("=" * 70)

    # 初始化数据库连接
    logger.info("📝 初始化数据库连接...")
    try:
        await init_db()
        logger.info("✅ 数据库连接成功")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        logger.error("💡 请确保MongoDB和Redis服务正在运行")
        return False

    try:
        # 1. 创建索引
        logger.info("📝 步骤1: 创建索引")
        if not await create_trading_calendar_indexes():
            logger.error("❌ 索引创建失败,终止初始化")
            return False

        # 2. 生成数据
        logger.info("\n📝 步骤2: 生成交易日历数据")
        count = await generate_trading_calendar_data(2020, 2025)
        if count == 0:
            logger.error("❌ 数据生成失败,终止初始化")
            return False

        # 3. 验证数据
        logger.info("\n📝 步骤3: 验证数据完整性")
        if not await validate_trading_calendar_data():
            logger.error("❌ 数据验证失败")
            return False

        logger.info("\n" + "=" * 70)
        logger.info("🎉 交易日历初始化完成!")
        logger.info("=" * 70)
        logger.info("\n💡 提示:")
        logger.info("  - 当前使用的是简化版交易日历(仅区分周末)")
        logger.info("  - 生产环境建议从专业金融数据源获取完整数据")
        logger.info("  - 例如: Tushare、AKShare 等提供的交易日历API")
        logger.info("\n📊 API端点:")
        logger.info("  - GET /api/backtest/trading-days?start_date=2024-01-01&end_date=2024-12-31")
        logger.info("  - GET /api/backtest/trading-days/2024-01-15")
        logger.info("  - GET /api/backtest/trading-days/2024-01-15/previous")
        logger.info("  - GET /api/backtest/trading-days/2024-01-15/next")
        logger.info("  - GET /api/backtest/trading-days/info?start_date=2024-01-01&end_date=2024-12-31")
        logger.info("=" * 70)

        return True
    finally:
        # 关闭数据库连接
        logger.info("\n📝 关闭数据库连接...")
        await close_db()
        logger.info("✅ 数据库连接已关闭")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行初始化
    asyncio.run(init_trading_calendar())
