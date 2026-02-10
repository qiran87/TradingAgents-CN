"""
回测执行引擎服务
负责执行回测任务、模拟交易过程、管理资金持仓
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio

from app.core.database import get_mongo_db, get_redis_client
from app.services.websocket_manager import get_websocket_manager
from app.strategies.dual_ma import DualMAStrategy

logger = logging.getLogger(__name__)


# ===================== 异常类 =====================

class BacktestEngineError(Exception):
    """回测引擎错误基类"""
    def __init__(self, message: str, code: str = "BACKTEST_ENGINE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BacktestNotFoundError(BacktestEngineError):
    """回测任务不存在错误"""
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id
        super().__init__(
            f"回测任务 {backtest_id} 不存在",
            "BACKTEST_NOT_FOUND"
        )


class InvalidBacktestStatusError(BacktestEngineError):
    """无效的回测状态错误"""
    def __init__(self, backtest_id: str, current_status: str, expected_status: List[str]):
        self.backtest_id = backtest_id
        self.current_status = current_status
        self.expected_status = expected_status
        super().__init__(
            f"回测任务 {backtest_id} 当前状态为 {current_status}，期望状态为 {expected_status}",
            "INVALID_BACKTEST_STATUS"
        )


class InsufficientFundsError(BacktestEngineError):
    """资金不足错误"""
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(
            f"资金不足：需要 ¥{required:.2f}，可用 ¥{available:.2f}",
            "INSUFFICIENT_FUNDS"
        )


class InsufficientPositionError(BacktestEngineError):
    """持仓不足错误"""
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"持仓不足：需要 {required}股，可用 {available}股",
            "INSUFFICIENT_POSITION"
        )


# ===================== 交易费用计算器 =====================

class TradingCostCalculator:
    """交易费用计算器"""

    @staticmethod
    def calculate_buy_cost(amount: float) -> Dict[str, float]:
        """
        计算买入费用

        Args:
            amount: 交易金额

        Returns:
            费用明细字典
        """
        # 佣金：万分之2.5，最低5元
        commission = max(amount * 0.00025, 5)

        # 过户费：万分之0.2（深圳）
        transfer_fee = amount * 0.00002

        total_cost = commission + transfer_fee

        return {
            "commission": round(commission, 2),
            "transfer_fee": round(transfer_fee, 2),
            "stamp_duty": 0.0,  # 买入无印花税
            "total_cost": round(total_cost, 2)
        }

    @staticmethod
    def calculate_sell_cost(amount: float) -> Dict[str, float]:
        """
        计算卖出费用

        Args:
            amount: 交易金额

        Returns:
            费用明细字典
        """
        # 佣金：万分之2.5，最低5元
        commission = max(amount * 0.00025, 5)

        # 印花税：千分之一（仅卖出）
        stamp_duty = amount * 0.001

        # 过户费：万分之0.2
        transfer_fee = amount * 0.00002

        total_cost = commission + stamp_duty + transfer_fee

        return {
            "commission": round(commission, 2),
            "stamp_duty": round(stamp_duty, 2),
            "transfer_fee": round(transfer_fee, 2),
            "total_cost": round(total_cost, 2)
        }


# ===================== 回测状态类 =====================

class BacktestState:
    """回测状态类"""

    def __init__(
        self,
        backtest_id: str,
        initial_capital: float,
        quotes: List[Dict],
        trading_days: List[str],
        parameters: Dict[str, Any] = None
    ):
        self.backtest_id = backtest_id
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0  # 持仓股数
        self.position_cost = 0.0  # 平均持仓成本
        self.quotes = quotes
        self.trading_days = trading_days
        self.parameters = parameters or {}  # 回测参数(包含策略参数等)

        # T+1规则：持仓批次列表
        # 每个批次记录买入日期、股数、成本
        self.position_lots: List[Dict[str, Any]] = []

    def add_position(self, shares: int, cost: float, date: str):
        """
        添加持仓批次

        Args:
            shares: 股数
            cost: 成本价
            date: 买入日期
        """
        self.position_lots.append({
            "shares": shares,
            "cost": cost,
            "buy_date": date
        })
        self.position += shares

        # 更新平均成本
        total_cost = self.position_cost * (self.position - shares) + cost * shares
        self.position_cost = total_cost / self.position if self.position > 0 else 0

    def can_sell(self, shares: int, current_date: str) -> bool:
        """
        检查是否可以卖出（T+1规则）

        Args:
            shares: 要卖出的股数
            current_date: 当前日期

        Returns:
            是否可以卖出
        """
        sellable_shares = 0
        for lot in self.position_lots:
            # T+1规则：买入日期不是当前日期的才能卖出
            if lot["buy_date"] != current_date:
                sellable_shares += lot["shares"]

        return sellable_shares >= shares

    def sell_position(self, shares: int) -> float:
        """
        卖出持仓（返回持仓成本）

        Args:
            shares: 要卖出的股数

        Returns:
            卖出部分的成本
        """
        remaining_shares = shares
        cost_basis = 0.0

        for lot in self.position_lots[:]:
            if remaining_shares == 0:
                break

            if lot["shares"] <= remaining_shares:
                # 完全卖出这个批次
                cost_basis += lot["shares"] * lot["cost"]
                remaining_shares -= lot["shares"]
                self.position_lots.remove(lot)
            else:
                # 部分卖出这个批次
                cost_basis += remaining_shares * lot["cost"]
                lot["shares"] -= remaining_shares
                remaining_shares = 0

        self.position -= shares

        # 更新平均成本
        if self.position > 0:
            # 重新计算剩余持仓的平均成本
            total_cost = sum(lot["shares"] * lot["cost"] for lot in self.position_lots)
            self.position_cost = total_cost / self.position
        else:
            self.position_cost = 0.0

        return cost_basis

    def get_market_value(self, current_price: float) -> float:
        """获取当前市值"""
        return self.position * current_price

    def get_total_assets(self, current_price: float) -> float:
        """获取总资产"""
        return self.cash + self.get_market_value(current_price)

    def get_profit_loss(self, current_price: float) -> float:
        """获取持仓盈亏"""
        if self.position == 0:
            return 0.0
        market_value = self.get_market_value(current_price)
        cost_basis = self.position * self.position_cost
        return market_value - cost_basis


# ===================== 回测引擎 =====================

class BacktestEngine:
    """回测执行引擎"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化回测引擎

        Args:
            db: MongoDB数据库实例
        """
        self.db = db
        self.websocket_manager = get_websocket_manager()

        # 任务控制标志
        self.should_pause = False
        self.should_abort = False

        # 回测参数（用于交易记录）
        self.stock_code: str = ""
        self.stock_name: str = ""

    async def execute_backtest(
        self,
        backtest_id: str,
        parameters: Dict[str, Any]
    ):
        """
        执行回测任务

        Args:
            backtest_id: 回测任务ID
            parameters: 回测参数
        """
        try:
            logger.info(f"🚀 开始执行回测任务: {backtest_id}")

            # 保存股票代码和名称（用于交易记录）
            self.stock_code = parameters.get("stock_code", "")
            self.stock_name = await self._get_stock_name(self.stock_code)

            # 1. 更新任务状态为运行中
            await self._update_task_status(backtest_id, "running")

            # 2. 获取行情数据和交易日历
            quotes = await self._get_quotes(parameters)
            trading_days = await self._get_trading_days(parameters)

            if not trading_days:
                raise BacktestEngineError("没有交易日数据")

            logger.info(f"📊 获取到 {len(trading_days)} 个交易日，{len(quotes)} 条行情数据")

            # 3. 初始化回测状态
            state = BacktestState(
                backtest_id=backtest_id,
                initial_capital=parameters["initial_capital"],
                quotes=quotes,
                trading_days=trading_days,
                parameters=parameters  # 传入完整参数,供策略使用
            )

            # 4. 执行回测循环
            total_bars = len(trading_days)
            start_time = datetime.now(timezone.utc)

            for i, trading_day in enumerate(trading_days):
                # 检查是否需要暂停
                if self.should_pause:
                    await self._pause_backtest(backtest_id, state, i)
                    break

                # 检查是否需要放弃
                if self.should_abort:
                    await self._abort_backtest(backtest_id)
                    return

                # 获取当日行情
                quote = self._get_quote_by_date(quotes, trading_day)
                if not quote:
                    logger.warning(f"⚠️  {trading_day} 没有行情数据，跳过")
                    continue

                # 执行策略（这里暂时使用简单的买入持有策略作为示例）
                # 实际应该从策略服务获取策略实例
                signal = self._execute_sample_strategy(state, quote, trading_day, i)

                # 执行交易
                if signal["action"] in ["buy", "sell"]:
                    await self._execute_trade(backtest_id, state, signal, quote, trading_day)

                # 更新每日状态
                await self._update_daily_state(backtest_id, state, quote, trading_day, i)

                # 更新进度
                progress = (i + 1) / total_bars * 100
                elapsed_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                estimated_remaining = elapsed_time / (i + 1) * (total_bars - i - 1) if i > 0 else None

                await self._update_progress(
                    backtest_id, i, total_bars, trading_day, progress,
                    elapsed_time, estimated_remaining
                )

                # 推送进度到WebSocket
                await self._send_progress_update(backtest_id, {
                    "current_bar": i + 1,
                    "total_bars": total_bars,
                    "percentage": round(progress, 2),
                    "current_date": trading_day,
                    "elapsed_time": elapsed_time,
                    "estimated_time_remaining": estimated_remaining
                })

                # 推送持仓更新
                await self._send_position_update(backtest_id, state, quote)

            # 5. 完成回测
            if not self.should_pause and not self.should_abort:
                await self._complete_backtest(backtest_id, state)
                logger.info(f"✅ 回测任务完成: {backtest_id}")

        except Exception as e:
            logger.error(f"❌ 回测任务执行失败: {backtest_id}, 错误: {e}", exc_info=True)
            await self._handle_error(backtest_id, e)

    def _execute_sample_strategy(
        self,
        state: BacktestState,
        quote: Dict,
        date: str,
        bar_index: int
    ) -> Dict[str, Any]:
        """
        执行双均线策略

        使用真正的DualMAStrategy进行回测

        Args:
            state: 回测状态
            quote: 当日行情
            date: 日期
            bar_index: K线索引

        Returns:
            交易信号
        """
        # 初始化策略(如果还没有初始化)
        if not hasattr(self, 'strategy'):
            # 获取策略参数
            strategy_params = state.parameters.get('strategy_params', {})

            # 兼容不同的参数名称
            short_window = strategy_params.get('short_window',
                           strategy_params.get('short_period', 5))
            long_window = strategy_params.get('long_window',
                           strategy_params.get('long_period', 20))

            # 初始化双均线策略
            params = {
                'short_window': short_window,
                'long_window': long_window
            }
            self.strategy = DualMAStrategy(params)
            logger.info(f"✅ 初始化双均线策略: short_window={short_window}, long_window={long_window}")

        # 调用策略生成信号
        timestamp = datetime.strptime(date, '%Y-%m-%d')
        signal = self.strategy.on_bar(
            bar_id=f"{date}_{bar_index}",
            timestamp=timestamp,
            current_price=quote['close'],
            position=state.position,
            cash=state.cash
        )

        return signal

    async def _get_stock_name(self, stock_code: str) -> str:
        """
        获取股票名称

        Args:
            stock_code: 股票代码

        Returns:
            股票名称，如果查询失败则返回股票代码
        """
        try:
            stock_info = await self.db.stock_info.find_one({"symbol": stock_code})
            if stock_info and "name" in stock_info:
                return stock_info["name"]
        except Exception as e:
            logger.warning(f"⚠️  获取股票名称失败: {stock_code}, 错误: {e}")

        # 如果查询失败，返回股票代码作为名称
        return stock_code

    async def _get_quotes(self, parameters: Dict[str, Any]) -> List[Dict]:
        """
        获取行情数据

        Args:
            parameters: 回测参数

        Returns:
            行情数据列表
        """
        from app.services.backtest_stock_data_service_v2 import BacktestStockDataService

        service = BacktestStockDataService(self.db, None)
        quotes = await service.get_quotes(
            parameters["stock_code"],
            parameters["start_date"],
            parameters["end_date"]
        )

        return quotes

    async def _get_trading_days(self, parameters: Dict[str, Any]) -> List[str]:
        """
        获取交易日列表

        Args:
            parameters: 回测参数

        Returns:
            交易日列表
        """
        from app.services.trading_calendar_service import TradingCalendarService

        service = TradingCalendarService(self.db)
        trading_days = await service.get_trading_days(
            parameters["start_date"],
            parameters["end_date"]
        )

        return trading_days

    def _get_quote_by_date(self, quotes: List[Dict], date: str) -> Optional[Dict]:
        """
        根据日期获取行情

        Args:
            quotes: 行情数据列表
            date: 日期

        Returns:
            行情数据
        """
        for quote in quotes:
            if quote["date"] == date:
                return quote
        return None

    async def _execute_trade(
        self,
        backtest_id: str,
        state: BacktestState,
        signal: Dict,
        quote: Dict,
        date: str
    ):
        """
        执行交易

        Args:
            backtest_id: 回测任务ID
            state: 回测状态
            signal: 交易信号
            quote: 行情数据
            date: 交易日期
        """
        if signal["action"] == "buy":
            await self._execute_buy(backtest_id, state, signal, quote, date)
        elif signal["action"] == "sell":
            await self._execute_sell(backtest_id, state, signal, quote, date)

    async def _execute_buy(
        self,
        backtest_id: str,
        state: BacktestState,
        signal: Dict,
        quote: Dict,
        date: str
    ):
        """
        执行买入

        Args:
            backtest_id: 回测任务ID
            state: 回测状态
            signal: 交易信号
            quote: 行情数据
            date: 交易日期
        """
        price = quote["close"]

        # 计算最大可买股数（100股倍数）
        max_shares = int(state.cash / price / 100) * 100

        if max_shares == 0:
            logger.info(f"💰 资金不足，无法买入: date={date}, cash={state.cash:.2f}, price={price:.2f}")
            return

        # 默认买入最大可买数量
        shares = min(signal.get("amount", max_shares), max_shares)
        shares = (shares // 100) * 100  # 确保100股倍数

        if shares == 0:
            return

        amount = shares * price

        # 计算费用
        cost_info = TradingCostCalculator.calculate_buy_cost(amount)
        total_cost = amount + cost_info["total_cost"]

        if total_cost > state.cash:
            logger.info(f"💰 资金不足: 需要={total_cost:.2f}, 可用={state.cash:.2f}")
            return

        # 更新状态
        cash_before = state.cash
        position_before = state.position
        state.cash -= total_cost
        # 计算单位总成本(包含手续费)
        unit_total_cost = total_cost / shares
        state.add_position(shares, unit_total_cost, date)

        # 记录交易
        trade_doc = {
            "backtest_id": backtest_id,
            "date": date,
            "trade_type": "buy",
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "price": price,
            "shares": shares,
            "amount": amount,
            "commission": cost_info["commission"],
            "stamp_duty": cost_info["stamp_duty"],
            "slippage": 0.0,
            "total_cost": total_cost,
            "cash_before": cash_before,
            "cash_after": state.cash,
            "position_before": position_before,
            "position_after": state.position,
            "profit_loss": 0.0,  # 买入时盈亏为0
            "signal": signal,
            "created_at": datetime.now(timezone.utc)
        }

        await self.db.backtest_trades.insert_one(trade_doc)
        logger.info(f"📈 买入: date={date}, shares={shares}, price={price:.2f}, total_cost={total_cost:.2f}")

        # 发送交易信号
        await self._send_trade_signal(
            backtest_id=backtest_id,
            trade_type="buy",
            price=price,
            shares=shares,
            amount=amount,
            date=date
        )

    async def _execute_sell(
        self,
        backtest_id: str,
        state: BacktestState,
        signal: Dict,
        quote: Dict,
        date: str
    ):
        """
        执行卖出

        Args:
            backtest_id: 回测任务ID
            state: 回测状态
            signal: 交易信号
            quote: 行情数据
            date: 交易日期
        """
        if state.position == 0:
            logger.info(f"📊 无持仓，无法卖出: date={date}")
            return

        # T+1检查
        sell_shares = min(signal.get("amount", state.position), state.position)
        if not state.can_sell(sell_shares, date):
            logger.info(f"🔒 T+1规则限制，无法卖出: date={date}, shares={sell_shares}")
            return

        # 调整为100股倍数
        sell_shares = (sell_shares // 100) * 100

        if sell_shares == 0:
            return

        price = quote["close"]
        amount = sell_shares * price

        # 计算费用
        cost_info = TradingCostCalculator.calculate_sell_cost(amount)
        total_cost = cost_info["total_cost"]

        # 更新状态
        cash_before = state.cash
        position_before = state.position
        cost_basis = state.sell_position(sell_shares)
        state.cash += amount - total_cost

        # 计算盈亏金额
        # 盈亏 = 卖出金额 - 手续费 - 成本基础
        # 注意: cost_basis已经是总成本,不需要再乘以sell_shares
        profit_loss = amount - total_cost - cost_basis

        # 记录交易
        trade_doc = {
            "backtest_id": backtest_id,
            "date": date,
            "trade_type": "sell",
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "price": price,
            "shares": sell_shares,
            "amount": amount,
            "commission": cost_info["commission"],
            "stamp_duty": cost_info["stamp_duty"],
            "slippage": 0.0,
            "total_cost": total_cost,
            "cash_before": cash_before,
            "cash_after": state.cash,
            "position_before": position_before,
            "position_after": state.position,
            "cost_basis": cost_basis,
            "profit_loss": profit_loss,  # 卖出时的盈亏
            "signal": signal,
            "created_at": datetime.now(timezone.utc)
        }

        await self.db.backtest_trades.insert_one(trade_doc)
        logger.info(f"📉 卖出: date={date}, shares={sell_shares}, price={price:.2f}, amount={amount:.2f}")

        # 发送交易信号
        await self._send_trade_signal(
            backtest_id=backtest_id,
            trade_type="sell",
            price=price,
            shares=sell_shares,
            amount=amount,
            date=date
        )

    async def _update_task_status(
        self,
        backtest_id: str,
        status: str
    ):
        """
        更新任务状态

        Args:
            backtest_id: 回测任务ID
            status: 新状态 (created/running/paused/completed/failed/aborted)
        """
        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"📊 任务状态更新: {backtest_id} -> {status}")

    async def _update_daily_state(
        self,
        backtest_id: str,
        state: BacktestState,
        quote: Dict,
        date: str,
        bar_index: int
    ):
        """
        更新每日状态

        Args:
            backtest_id: 回测任务ID
            state: 回测状态
            quote: 行情数据
            date: 日期
            bar_index: K线索引
        """
        market_value = state.get_market_value(quote["close"])
        total_assets = state.get_total_assets(quote["close"])
        profit_loss = state.get_profit_loss(quote["close"])

        # 计算收益率
        daily_return = 0.0
        if bar_index > 0:
            prev_assets = await self._get_previous_total_assets(backtest_id, bar_index)
            if prev_assets and prev_assets > 0:
                daily_return = (total_assets - prev_assets) / prev_assets

        cumulative_return = (total_assets - state.initial_capital) / state.initial_capital

        daily_state_doc = {
            "backtest_id": backtest_id,
            "date": date,
            "bar_index": bar_index,
            "cash": round(state.cash, 2),
            "position": state.position,
            "position_cost": round(state.position_cost, 2),
            "current_price": quote["close"],
            "market_value": round(market_value, 2),
            "total_assets": round(total_assets, 2),
            "daily_return": round(daily_return, 4),
            "cumulative_return": round(cumulative_return, 4),
            "profit_loss": round(profit_loss, 2),
            "created_at": datetime.now(timezone.utc)
        }

        await self.db.backtest_daily_states.insert_one(daily_state_doc)

    async def _get_previous_total_assets(self, backtest_id: str, bar_index: int) -> Optional[float]:
        """获取前一日总资产"""
        if bar_index == 0:
            return None

        prev_state = await self.db.backtest_daily_states.find_one({
            "backtest_id": backtest_id,
            "bar_index": bar_index - 1
        })

        return prev_state["total_assets"] if prev_state else None

    async def _update_progress(
        self,
        backtest_id: str,
        current_bar: int,
        total_bars: int,
        current_date: str,
        progress: float,
        elapsed_time: float,
        estimated_time_remaining: Optional[float]
    ):
        """更新进度"""
        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "execution_info.current_bar_index": current_bar,
                "execution_info.total_bars": total_bars,
                "execution_info.current_date": current_date,
                "execution_info.progress": round(progress, 2),
                "execution_info.elapsed_time": round(elapsed_time, 2),
                "execution_info.estimated_time_remaining": round(estimated_time_remaining, 2) if estimated_time_remaining else None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

    async def _send_progress_update(self, backtest_id: str, progress_data: dict):
        """发送进度更新到WebSocket"""
        message = {
            "type": "progress",
            "data": {
                "backtest_id": backtest_id,
                "status": "running",
                "progress": progress_data
            }
        }
        await self.websocket_manager.send_progress_update(backtest_id, message)

    async def _send_position_update(self, backtest_id: str, state: BacktestState, quote: Dict):
        """发送持仓更新到WebSocket"""
        market_value = state.get_market_value(quote["close"])
        total_assets = state.get_total_assets(quote["close"])
        profit_loss = state.get_profit_loss(quote["close"])
        profit_loss_pct = (profit_loss / (state.position * state.position_cost)) * 100 if state.position > 0 else 0

        position_data = {
            "backtest_id": backtest_id,
            "position": {
                "cash": round(state.cash, 2),
                "position": state.position,
                "position_cost": round(state.position_cost, 2),
                "current_price": quote["close"],
                "market_value": round(market_value, 2),
                "total_assets": round(total_assets, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percentage": round(profit_loss_pct, 2)
            }
        }

        message = {
            "type": "position_update",
            "data": position_data
        }
        await self.websocket_manager.send_progress_update(backtest_id, message)

    async def _send_trade_signal(
        self,
        backtest_id: str,
        trade_type: str,
        price: float,
        shares: int,
        amount: float,
        date: str
    ):
        """
        发送交易信号到WebSocket

        Args:
            backtest_id: 回测任务ID
            trade_type: 交易类型 (buy/sell)
            price: 成交价格
            shares: 成交数量
            amount: 成交金额
            date: 交易日期
        """
        message = {
            "type": "trade_signal",
            "data": {
                "backtest_id": backtest_id,
                "trade": {
                    "type": trade_type,
                    "date": date,
                    "price": round(price, 2),
                    "shares": shares,
                    "amount": round(amount, 2)
                }
            }
        }
        await self.websocket_manager.send_progress_update(backtest_id, message)

    async def _send_error_message(
        self,
        backtest_id: str,
        error: Exception
    ):
        """
        发送错误信息到WebSocket

        Args:
            backtest_id: 回测任务ID
            error: 异常对象
        """
        message = {
            "type": "error",
            "data": {
                "backtest_id": backtest_id,
                "error": {
                    "code": type(error).__name__,
                    "message": str(error)
                }
            }
        }
        await self.websocket_manager.send_progress_update(backtest_id, message)

    async def _complete_backtest(self, backtest_id: str, state: BacktestState):
        """完成回测"""
        # 获取最后一日的行情
        last_quote = state.quotes[-1] if state.quotes else None
        final_value = state.get_total_assets(last_quote["close"]) if last_quote else state.cash

        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "status": "completed",
                "execution_info.end_time": datetime.now(timezone.utc),
                "execution_info.final_value": round(final_value, 2),
                "execution_info.total_return": round((final_value - state.initial_capital) / state.initial_capital * 100, 2),
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # 自动计算并保存回测结果
        try:
            from app.services.result_calculator import get_result_calculator_service
            calculator = get_result_calculator_service()
            await calculator.calculate_and_save_results(backtest_id)
            logger.info(f"✅ 回测结果已自动计算并保存: {backtest_id}")
        except Exception as e:
            logger.error(f"⚠️  自动计算回测结果失败: {backtest_id}, 错误: {e}", exc_info=True)
            # 结果计算失败不影响回测完成状态

    async def _pause_backtest(self, backtest_id: str, state: BacktestState, bar_index: int):
        """暂停回测"""
        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "status": "paused",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"⏸️  回测任务已暂停: {backtest_id}")

    async def _abort_backtest(self, backtest_id: str):
        """放弃回测"""
        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "status": "aborted",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"🚫 回测任务已放弃: {backtest_id}")

    async def _handle_error(self, backtest_id: str, error: Exception):
        """处理错误"""
        await self.db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {
                "status": "error",
                "error": {
                    "code": type(error).__name__,
                    "message": str(error),
                    "stack_trace": str(error.__traceback__) if error.__traceback__ else None
                },
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # 发送错误信息到WebSocket
        await self._send_error_message(backtest_id, error)

    async def pause_execution(self):
        """设置暂停标志"""
        self.should_pause = True

    async def abort_execution(self):
        """设置放弃标志"""
        self.should_abort = True
        self.should_pause = False

    async def resume_execution(self):
        """恢复执行"""
        self.should_pause = False


# ===================== 依赖注入 =====================

_backtest_engine_service = None


def get_backtest_engine_service() -> BacktestEngine:
    """获取回测引擎服务实例"""
    global _backtest_engine_service
    if _backtest_engine_service is None:
        db = get_mongo_db()
        _backtest_engine_service = BacktestEngine(db)
    return _backtest_engine_service


# ===================== 后台任务执行函数 =====================

async def execute_backtest_task(backtest_id: str, parameters: Dict[str, Any]):
    """
    后台执行回测任务

    Args:
        backtest_id: 回测任务ID
        parameters: 回测参数
    """
    # 每次都创建新的引擎实例,避免后台任务上下文问题
    db = get_mongo_db()
    engine = BacktestEngine(db)
    await engine.execute_backtest(backtest_id, parameters)
