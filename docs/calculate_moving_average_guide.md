# 移动平均线计算工具使用说明

## 工具位置

`app/scripts/calculate_moving_average.py`

## 功能说明

这个脚本用于计算指定股票在指定日期的移动平均线价格,使用数据库`stock_daily_quotes`表中的历史K线数据。

## 使用方法

### 基本语法

```bash
python3 -m app.scripts.calculate_moving_average <symbol> <trade_date> <period>
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `symbol` | 股票代码 | `000001`, `000001.SZ`, `600000`, `600000.SH` |
| `trade_date` | 交易日期 | `2026-02-10` (格式: YYYY-MM-DD) |
| `period` | 均线周期 | `5`, `10`, `20`, `50`, `120`, `250` |

## 使用示例

### 示例1: 计算20日均线

```bash
python3 -m app.scripts.calculate_moving_average 000001 2026-02-06 20
```

**输出**:
```
📊 查询条件:
  股票代码: 000001 (标准化为: 000001)
  目标日期: 2026-02-06
  均线周期: 20日
  查询范围: 2025-12-28 至 2026-02-06

📈 查询结果:
  找到 25 条K线数据
  有效收盘价: 25 条

✅ 计算结果:
  20日均线价格: ¥11.08

📋 使用的最后 20 个交易日数据:
  1. 2026-01-12: ¥11.48
  2. 2026-01-13: ¥11.47
  ...
  20. 2026-02-06: ¥11.05

🎯 最终结果: 000001 在 2026-02-06 的 20日均线价格为 ¥11.08
```

### 示例2: 计算50日均线

```bash
python3 -m app.scripts.calculate_moving_average 000001 2026-02-06 50
```

**输出**:
```
📊 查询条件:
  股票代码: 000001
  目标日期: 2026-02-06
  均线周期: 50日
  查询范围: 2025-10-29 至 2026-02-06

📈 查询结果:
  找到 25 条K线数据
⚠️  警告: 数据不足!
   需要 50 条数据
   实际有 25 条数据
   可用数据范围: 2026-01-05 至 2026-02-06

💡 使用实际可用的 25 日均线计算:
   25日均线价格: ¥11.17

🎯 最终结果: 000001 在 2026-02-06 的 50日均线价格为 ¥11.17
```

### 示例3: 计算5日均线

```bash
python3 -m app.scripts.calculate_moving_average 000001.SZ 2026-02-06 5
```

### 示例4: 计算120日均线

```bash
python3 -m app.scripts.calculate_moving_average 600000 2025-12-31 120
```

## 输出说明

### 正常情况

当数据充足时,输出包括:
1. **查询条件** - 显示查询参数
2. **查询结果** - 显示找到的数据量
3. **计算结果** - 显示均线价格
4. **使用的数据** - 列出使用的所有交易日
5. **最终结果** - 一行总结

### 数据不足

当数据不足时,会:
1. ⚠️ 显示警告信息
2. 💡 使用实际可用数据计算
3. 显示实际使用的周期数

### 错误情况

可能的错误:
- ❌ 没有找到股票数据
- ❌ 有效收盘价数据不足
- ❌ 日期格式错误

## 数据来源

- **数据库**: MongoDB (`tradingagents`)
- **集合**: `stock_daily_quotes`
- **字段**: `close` (优先) 或 `pre_close`

## 查询逻辑

1. **标准化股票代码**: 取前6位数字
2. **计算查询范围**: 目标日期向前推 `period × 2` 天
3. **查询历史数据**: 按日期升序排序
4. **提取收盘价**: 优先使用`close`字段
5. **计算均线**: 取最后`period`条数据的平均值

## 常见均线周期

| 周期 | 名称 | 用途 |
|------|------|------|
| 5 | 5日均线 | 短期趋势 |
| 10 | 10日均线 | 短期趋势 |
| 20 | 20日均线 | 月线趋势 |
| 50 | 50日均线 | 中期趋势 |
| 120 | 120日均线 | 半年趋势 |
| 250 | 250日均线 | 年线趋势 |

## 注意事项

1. **日期格式**: 必须使用 `YYYY-MM-DD` 格式
2. **股票代码**: 支持多种格式(000001, 000001.SZ, 600000等)
3. **数据充足性**: 需要确保数据库中有足够的历史数据
4. **交易日**: 只计算交易日,周末和节假日不包括在内

## 故障排查

### 问题1: 找不到股票数据

**可能原因**:
- 股票代码不正确
- 数据库中没有该股票的数据

**解决方法**:
```bash
# 检查数据库中是否有该股票的数据
python3 << 'EOF'
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check():
    client = AsyncIOMotorClient("mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin")
    db = client.tradingagents

    count = await db.stock_daily_quotes.count_documents({"symbol": {"$regex": "^000001"}})
    print(f"000001相关的数据: {count} 条")

    client.close()

asyncio.run(check())
EOF
```

### 问题2: 数据不足

**可能原因**:
- 目标日期太早,数据库中没有足够的历史数据
- 查询范围设置不合理

**解决方法**:
- 选择更近的日期
- 使用更短的周期

### 问题3: 权限错误

**错误信息**: `pymongo.errors.OperationFailure: not authorized`

**解决方法**:
- 检查`.env`文件中的数据库配置
- 确认用户名和密码正确

## 性能说明

- **查询速度**: 通常 < 100ms
- **数据范围**: 默认查询 `period × 2` 天的数据
- **内存占用**: 最小化,只加载必要的数据

## 扩展功能

### 批量计算多个股票

```bash
# 计算多个股票的5日均线
for stock in 000001 000002 600000; do
    echo "计算 $stock"
    python3 -m app.scripts.calculate_moving_average $stock 2026-02-06 5
done
```

### 计算多个周期

```bash
# 计算多个周期的均线
for period in 5 10 20 50; do
    echo "计算 ${period}日均线"
    python3 -m app.scripts.calculate_moving_average 000001 2026-02-06 $period
done
```

### 保存到文件

```bash
# 将结果保存到文件
python3 -m app.scripts.calculate_moving_average 000001 2026-02-06 20 > ma_result.txt
```

## 相关文档

- [K线数据存储说明](./kline_data_storage.md)
- [双均线策略验证](./dual_ma_strategy_verification.md)
- [回测执行流程](./backtest_execution_flow.md)

---

**创建时间**: 2026-02-10
**维护者**: TradingAgents-CN Team
**版本**: v1.0.0
