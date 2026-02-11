#!/usr/bin/env python3
"""
计算指定股票、日期的移动平均线价格

使用方法:
    python3 -m app.scripts.calculate_moving_average <symbol> <trade_date> <period>

示例:
    # 计算000001在2026-02-10的50日均线
    python3 -m app.scripts.calculate_moving_average 000001 2026-02-10 50

    # 计算000001.SZ在2026-02-10的20日均线
    python3 -m app.scripts.calculate_moving_average 000001.SZ 2026-02-10 20

    # 计算600000在2025-12-31的5日均线
    python3 -m app.scripts.calculate_moving_average 600000 2025-12-31 5
"""

import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()


async def calculate_moving_average(symbol: str, trade_date: str, period: int):
    """
    计算移动平均线价格

    Args:
        symbol: 股票代码 (如 000001, 000001.SZ, 600000)
        trade_date: 交易日期 (格式: YYYY-MM-DD)
        period: 均线周期 (如 5, 10, 20, 50, 120, 250)

    Returns:
        移动平均价格,如果数据不足则返回None
    """
    # 连接MongoDB
    mongo_url = f"mongodb://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@{os.getenv('MONGODB_HOST')}:{os.getenv('MONGODB_PORT')}/tradingagents?authSource=admin"
    client = AsyncIOMotorClient(mongo_url)
    db = client.tradingagents

    # 标准化股票代码 (去除后缀)
    code_6 = symbol[:6]  # 取前6位

    # 计算需要的开始日期 (向前推period天)
    target_date = datetime.strptime(trade_date, "%Y-%m-%d")

    # 多取一些数据以确保有足够的交易日 (考虑到周末和节假日)
    days_needed = period * 2  # 取2倍周期,以确保有足够的交易日
    start_date = target_date - timedelta(days=days_needed)

    print(f"📊 查询条件:")
    print(f"  股票代码: {symbol} (标准化为: {code_6})")
    print(f"  目标日期: {trade_date}")
    print(f"  均线周期: {period}日")
    print(f"  查询范围: {start_date.strftime('%Y-%m-%d')} 至 {trade_date}")

    # 查询历史数据
    # 注意:数据库中的trade_date格式是 YYYY-MM-DD
    query = {
        "symbol": {"$regex": f"^{code_6}"},
        "trade_date": {
            "$gte": start_date.strftime("%Y-%m-%d"),
            "$lte": target_date.strftime("%Y-%m-%d")
        }
    }

    cursor = db.stock_daily_quotes.find(query).sort("trade_date", 1)
    quotes = await cursor.to_list(length=None)

    print(f"\n📈 查询结果:")
    print(f"  找到 {len(quotes)} 条K线数据")

    if not quotes:
        print(f"❌ 错误: 没有找到股票 {symbol} 的数据")
        client.close()
        return None

    # 检查是否有足够的数据
    if len(quotes) < period:
        print(f"⚠️  警告: 数据不足!")
        print(f"   需要 {period} 条数据")
        print(f"   实际有 {len(quotes)} 条数据")
        print(f"   可用数据范围: {quotes[0]['trade_date']} 至 {quotes[-1]['trade_date']}")

        # 使用实际可用数据计算
        available_period = len(quotes)
        print(f"\n💡 使用实际可用的 {available_period} 日均线计算:")

        close_prices = [q.get("close") or q.get("pre_close", 0) for q in quotes]
        valid_prices = [p for p in close_prices if p > 0]

        if len(valid_prices) < available_period:
            print(f"❌ 错误: 有效价格数据不足 ({len(valid_prices)}/{available_period})")
            client.close()
            return None

        ma_value = sum(valid_prices[-available_period:]) / available_period
        print(f"   {available_period}日均线价格: ¥{ma_value:.4f}")

        client.close()
        return ma_value

    # 提取收盘价 (优先使用close,如果没有则使用pre_close)
    close_prices = []
    for quote in quotes:
        close_price = quote.get("close")
        if close_price is None or close_price == 0:
            close_price = quote.get("pre_close")
        if close_price is not None and close_price > 0:
            close_prices.append(close_price)

    print(f"  有效收盘价: {len(close_prices)} 条")

    # 检查数据是否充足
    if len(close_prices) < period:
        print(f"❌ 错误: 有效收盘价数据不足 ({len(close_prices)}/{period})")
        client.close()
        return None

    # 取最后period条数据计算均线
    prices_for_ma = close_prices[-period:]
    ma_value = sum(prices_for_ma) / period

    print(f"\n✅ 计算结果:")
    print(f"  {period}日均线价格: ¥{ma_value:.4f}")

    # 显示详细的数据
    print(f"\n📋 使用的最后 {period} 个交易日数据:")
    for i, (quote, price) in enumerate(zip(quotes[-period:], prices_for_ma)):
        print(f"  {i+1}. {quote['trade_date']}: ¥{price:.2f}")

    client.close()
    return ma_value


async def main():
    """主函数"""
    if len(sys.argv) != 4:
        print("❌ 错误: 参数不足")
        print("\n使用方法:")
        print("  python3 -m app.scripts.calculate_moving_average <symbol> <trade_date> <period>")
        print("\n参数说明:")
        print("  symbol    - 股票代码 (如: 000001, 000001.SZ, 600000)")
        print("  trade_date - 交易日期 (格式: YYYY-MM-DD, 如: 2026-02-10)")
        print("  period    - 均线周期 (如: 5, 10, 20, 50, 120, 250)")
        print("\n示例:")
        print("  python3 -m app.scripts.calculate_moving_average 000001 2026-02-10 50")
        print("  python3 -m app.scripts.calculate_moving_average 000001.SZ 2025-12-31 20")
        sys.exit(1)

    symbol = sys.argv[1]
    trade_date = sys.argv[2]
    period_str = sys.argv[3]

    # 验证参数
    try:
        period = int(period_str)
        if period <= 0:
            raise ValueError("周期必须大于0")
    except ValueError as e:
        print(f"❌ 错误: 周期参数无效 - {e}")
        print(f"   请输入正整数,如: 5, 10, 20, 50, 120, 250")
        sys.exit(1)

    # 验证日期格式
    try:
        datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ 错误: 日期格式无效 - {trade_date}")
        print(f"   请使用格式: YYYY-MM-DD (如: 2026-02-10)")
        sys.exit(1)

    # 计算均线
    result = await calculate_moving_average(symbol, trade_date, period)

    if result is not None:
        print(f"\n🎯 最终结果: {symbol} 在 {trade_date} 的 {period}日均线价格为 ¥{result:.4f}")
    else:
        print(f"\n❌ 计算失败: 无法计算 {symbol} 在 {trade_date} 的 {period}日均线")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
