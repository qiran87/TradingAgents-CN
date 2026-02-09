# 交易明细显示问题修复记录

## 问题描述

在回测历史记录的"交易明细"模块中,虽然数据库 `backtest_trades` 集合中有交易记录,但前端无法显示数据。

## 根本原因

数据库中的旧交易记录缺少前端必需的字段:
- `stock_code` - 股票代码
- `stock_name` - 股票名称
- `cash_before` - 交易前现金
- `position_before` - 交易前持仓

### 问题分析

1. **后端代码正确**: `app/services/backtest_engine_service.py` 中 `_execute_buy()` 和 `_execute_sell()` 方法在写入交易时已经包含所有必需字段(第563-583行和第650-671行)

2. **旧数据缺失**: 数据库中已有的交易记录是在代码完善之前创建的,因此缺少这些字段

3. **前端显示要求**: `frontend/src/components/BacktestResults.vue` 中的表格需要这些字段来显示完整信息

## 修复方案

创建了 `scripts/fix_trade_fields.py` 脚本来修复旧数据:

1. **从 backtest_tasks 获取股票信息**:
   - 读取 `parameters.stock_code` 和 `parameters.stock_name`
   - 补充到每条交易记录中

2. **从交易序列推算交易前后状态**:
   - 按日期顺序处理每条交易
   - 根据交易类型(buy/sell)和金额计算 `cash_before` 和 `position_before`
   - 更新状态为下一条交易做准备

## 修复结果

修复后的交易记录包含所有必需字段:
```json
{
  "stock_code": "000001.SZ",
  "stock_name": "000001.SZ",
  "price": 10.5,
  "shares": 1000,
  "amount": 10500.0,
  "cash_before": 100000.0,
  "position_before": 0,
  "cash_after": 50000,
  "position_after": 1000,
  ...
}
```

## 验证步骤

1. 运行修复脚本:
   ```bash
   ./venv/bin/python3 scripts/fix_trade_fields.py
   ```

2. 验证字段完整性:
   ```bash
   ./venv/bin/python3 -c "
   import asyncio
   from motor.motor_asyncio import AsyncIOMotorClient

   async def verify():
       client = AsyncIOMotorClient('mongodb://admin:tradingagents123@localhost:27017')
       db = client.tradingagents
       trade = await db.backtest_trades.find_one({})
       required = ['stock_code', 'stock_name', 'cash_before', 'position_before']
       for field in required:
           assert field in trade, f'缺少字段: {field}'
       print('✅ 所有字段完整')
       client.close()

   asyncio.run(verify())
   "
   ```

3. 在前端查看交易明细:
   - 打开回测历史记录页面
   - 点击某个回测任务
   - 滚动到"交易明细"模块
   - 确认表格正确显示所有交易记录

## 后续建议

1. **预防措施**: 新的回测任务会自动包含所有字段,无需额外处理

2. **数据迁移**: 如果有其他环境的旧数据,运行相同的修复脚本即可

3. **代码审查**: 确保回测引擎代码保持当前的字段完整性

## 相关文件

- 后端交易写入逻辑: `app/services/backtest_engine_service.py:563-671`
- 前端交易明细组件: `frontend/src/components/BacktestResults.vue:224-307`
- 后端API接口: `app/routers/backtest_engine.py:491-540`
- 修复脚本: `scripts/fix_trade_fields.py`

## 时间记录

- 问题发现: 2026-02-09
- 问题定位: 通过检查数据库结构和前后端代码
- 修复完成: 2026-02-09
- 验证通过: 所有字段完整,前端正常显示
