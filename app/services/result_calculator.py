"""
回测结果计算服务
负责回测完成后的结果计算和统计分析，生成收益率、最大回撤、胜率等关键指标
"""
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone

from app.core.response import ok, fail

logger = logging.getLogger(__name__)


# ===================== 异常类 =====================

class ResultCalculatorError(Exception):
    """结果计算器错误基类"""
    def __init__(self, message: str, code: str = "RESULT_CALCULATOR_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BacktestNotFoundError(ResultCalculatorError):
    """回测任务不存在错误"""
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id
        super().__init__(
            f"回测任务 {backtest_id} 不存在",
            "BACKTEST_NOT_FOUND"
        )


class InsufficientDataError(ResultCalculatorError):
    """数据不足错误"""
    def __init__(self, message: str):
        super().__init__(
            f"数据不足: {message}",
            "INSUFFICIENT_DATA"
        )


# ===================== 结果计算服务 =====================

class ResultCalculator:
    """回测结果计算器"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化结果计算器

        Args:
            db: MongoDB数据库实例
        """
        self.db = db

    async def calculate_and_save_results(
        self,
        backtest_id: str
    ) -> Dict[str, Any]:
        """
        计算并保存回测结果

        Args:
            backtest_id: 回测任务ID

        Returns:
            计算结果字典
        """
        try:
            logger.info(f"📊 开始计算回测结果: {backtest_id}")

            # 1. 获取回测任务信息
            task = await self.db.backtest_tasks.find_one({"backtest_id": backtest_id})
            if not task:
                raise BacktestNotFoundError(backtest_id)

            # 2. 获取每日状态数据
            daily_states = await self._get_daily_states(backtest_id)
            if not daily_states:
                raise InsufficientDataError("没有每日状态数据")

            # 3. 获取交易数据
            trades = await self._get_trades(backtest_id)

            # 4. 计算所有指标
            results = {
                "backtest_id": backtest_id,
                "strategy_id": task.get("parameters", {}).get("strategy_id", "unknown"),
                "return_metrics": self._calculate_return_metrics(daily_states),
                "risk_metrics": self._calculate_risk_metrics(daily_states),
                "risk_adjusted_metrics": self._calculate_risk_adjusted_metrics(daily_states),
                "trading_stats": self._calculate_trading_stats(trades),
                "equity_curve": self._calculate_equity_curve(daily_states),
                "created_at": datetime.now(timezone.utc)
            }

            # 5. 保存结果到数据库
            await self._save_results(backtest_id, results)

            logger.info(f"✅ 回测结果计算完成: {backtest_id}")

            return results

        except BacktestNotFoundError:
            raise
        except InsufficientDataError:
            raise
        except Exception as e:
            logger.error(f"❌ 计算回测结果失败: {backtest_id}, 错误: {e}", exc_info=True)
            raise ResultCalculatorError(f"计算结果失败: {str(e)}")

    async def get_results(
        self,
        backtest_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取回测结果

        Args:
            backtest_id: 回测任务ID

        Returns:
            结果字典，如果不存在返回None
        """
        result = await self.db.backtest_results.find_one({"backtest_id": backtest_id})

        if result:
            result.pop("_id", None)  # 移除MongoDB的_id字段

        return result

    async def get_equity_curve(
        self,
        backtest_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取资金曲线

        Args:
            backtest_id: 回测任务ID

        Returns:
            资金曲线数据，如果不存在返回None
        """
        result = await self.get_results(backtest_id)

        if result and "equity_curve" in result:
            return result["equity_curve"]

        return None

    async def get_trades(
        self,
        backtest_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        获取交易明细

        Args:
            backtest_id: 回测任务ID
            limit: 最大返回数量

        Returns:
            交易列表
        """
        cursor = self.db.backtest_trades.find({"backtest_id": backtest_id}).sort("date", 1)
        trades = await cursor.to_list(length=limit)

        # 移除_id字段
        for trade in trades:
            trade.pop("_id", None)

        return trades

    async def _get_daily_states(
        self,
        backtest_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取每日状态数据

        Args:
            backtest_id: 回测任务ID

        Returns:
            每日状态列表（按日期排序）
        """
        cursor = self.db.backtest_daily_states.find(
            {"backtest_id": backtest_id}
        ).sort("bar_index", 1)

        daily_states = await cursor.to_list(length=None)

        return daily_states

    async def _get_trades(
        self,
        backtest_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取交易数据

        Args:
            backtest_id: 回测任务ID

        Returns:
            交易列表
        """
        cursor = self.db.backtest_trades.find(
            {"backtest_id": backtest_id}
        ).sort("date", 1)

        trades = await cursor.to_list(length=None)

        return trades

    async def _save_results(
        self,
        backtest_id: str,
        results: Dict[str, Any]
    ):
        """
        保存结果到数据库

        Args:
            backtest_id: 回测任务ID
            results: 结果字典
        """
        # 使用upsert：如果存在则更新，不存在则插入
        await self.db.backtest_results.update_one(
            {"backtest_id": backtest_id},
            {"$set": results},
            upsert=True
        )

    def _calculate_return_metrics(self, daily_states: List[Dict]) -> Dict[str, Any]:
        """
        计算收益指标

        Args:
            daily_states: 每日状态列表

        Returns:
            收益指标字典
        """
        # 数据验证
        if not daily_states:
            logger.warning("每日状态数据为空，返回默认值")
            return {
                "total_return": 0.0,
                "annual_return": 0.0,
                "cumulative_returns": [],
                "daily_returns": []
            }

        # 验证必需字段
        required_fields = ["total_assets", "date", "bar_index"]
        for i, state in enumerate(daily_states):
            missing_fields = [f for f in required_fields if f not in state]
            if missing_fields:
                raise ValueError(
                    f"每日状态数据缺少必要字段: 索引={i}, 缺少字段={missing_fields}, 数据={state}"
                )

        total_assets = [state["total_assets"] for state in daily_states]
        initial_capital = total_assets[0]

        # 总收益率
        final_assets = total_assets[-1]
        total_return = (final_assets - initial_capital) / initial_capital

        # 日收益率（从数据库中读取，如果不存在则计算）
        daily_returns = []
        for state in daily_states:
            if "daily_return" in state:
                daily_returns.append(state["daily_return"])
            else:
                # 如果数据库中没有daily_return，则计算
                idx = daily_states.index(state)
                if idx > 0:
                    daily_return = (state["total_assets"] - daily_states[idx-1]["total_assets"]) / daily_states[idx-1]["total_assets"]
                    daily_returns.append(daily_return)

        # 累计收益率
        cumulative_returns = []
        cumulative_return = 0.0
        for daily_return in daily_returns:
            cumulative_return = (1 + cumulative_return) * (1 + daily_return) - 1
            cumulative_returns.append(cumulative_return)

        # 年化收益率
        days = len(daily_states)
        if days > 0 and total_return > -1:  # 避免负数导致的开方错误
            annual_return = (1 + total_return) ** (365 / days) - 1
        else:
            annual_return = 0.0

        return {
            "total_return": round(total_return, 4),
            "annual_return": round(annual_return, 4),
            "cumulative_returns": [round(r, 4) for r in cumulative_returns],
            "daily_returns": [round(r, 4) for r in daily_returns]
        }

    def _calculate_risk_metrics(self, daily_states: List[Dict]) -> Dict[str, Any]:
        """
        计算风险指标

        Args:
            daily_states: 每日状态列表

        Returns:
            风险指标字典
        """
        # 数据验证
        if not daily_states:
            logger.warning("每日状态数据为空，返回默认风险指标")
            return {
                "max_drawdown": 0.0,
                "volatility": 0.0,
                "downside_volatility": 0.0,
                "var_95": 0.0
            }

        # 验证必需字段
        required_fields = ["total_assets", "date"]
        for i, state in enumerate(daily_states):
            missing_fields = [f for f in required_fields if f not in state]
            if missing_fields:
                raise ValueError(
                    f"每日状态数据缺少必要字段: 索引={i}, 缺少字段={missing_fields}"
                )

        total_assets = [state["total_assets"] for state in daily_states]
        initial_capital = total_assets[0]

        # 计算最大回撤
        max_drawdown = 0.0
        peak = initial_capital

        for assets in total_assets:
            if assets > peak:
                peak = assets

            drawdown = (peak - assets) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 日收益率
        daily_returns = []
        for i, state in enumerate(daily_states):
            if i > 0:
                daily_return = (state["total_assets"] - daily_states[i-1]["total_assets"]) / daily_states[i-1]["total_assets"]
                daily_returns.append(daily_return)

        # 波动率（年化）
        if daily_returns:
            volatility = float(np.std(daily_returns)) * np.sqrt(252)
        else:
            volatility = 0.0

        # 下行波动率
        negative_returns = [r for r in daily_returns if r < 0]
        if negative_returns:
            downside_volatility = float(np.std(negative_returns)) * np.sqrt(252)
        else:
            downside_volatility = 0.0

        # VaR 95%（风险价值）
        if daily_returns:
            var_95 = float(np.percentile(daily_returns, 5))
        else:
            var_95 = 0.0

        return {
            "max_drawdown": round(max_drawdown, 4),
            "volatility": round(volatility, 4),
            "downside_volatility": round(downside_volatility, 4),
            "var_95": round(var_95, 4)
        }

    def _calculate_risk_adjusted_metrics(
        self,
        daily_states: List[Dict]
    ) -> Dict[str, Any]:
        """
        计算风险调整收益指标

        Args:
            daily_states: 每日状态列表

        Returns:
            风险调整收益指标字典
        """
        return_metrics = self._calculate_return_metrics(daily_states)
        risk_metrics = self._calculate_risk_metrics(daily_states)

        # 无风险利率（3%）
        risk_free_rate = 0.03

        # 夏普比率 = (年化收益 - 无风险利率) / 波动率
        excess_return = return_metrics["annual_return"] - risk_free_rate
        sharpe_ratio = excess_return / risk_metrics["volatility"] if risk_metrics["volatility"] > 0 else 0.0

        # 索提诺比率 = (年化收益 - 无风险利率) / 下行波动率
        sortino_ratio = excess_return / risk_metrics["downside_volatility"] if risk_metrics["downside_volatility"] > 0 else 0.0

        # 卡玛比率 = 年化收益 / 最大回撤
        calmar_ratio = return_metrics["annual_return"] / risk_metrics["max_drawdown"] if risk_metrics["max_drawdown"] > 0 else 0.0

        return {
            "sharpe_ratio": round(sharpe_ratio, 4),
            "sortino_ratio": round(sortino_ratio, 4),
            "calmar_ratio": round(calmar_ratio, 4)
        }

    def _calculate_trading_stats(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        计算交易统计

        Args:
            trades: 交易列表

        Returns:
            交易统计字典
        """
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "profit_loss_ratio": 0.0
            }

        # 分离买卖交易
        buy_trades = [t for t in trades if t["trade_type"] == "buy"]
        sell_trades = [t for t in trades if t["trade_type"] == "sell"]

        # 检查未平仓交易
        unpaired_count = max(0, len(buy_trades) - len(sell_trades))
        if unpaired_count > 0:
            logger.warning(f"⚠️ 发现{unpaired_count}笔未平仓买入交易未计入交易统计")

        # 配对买卖交易计算盈亏
        paired_trades = self._pair_trades(buy_trades, sell_trades)

        total_trades = len(paired_trades)
        winning_trades = [t for t in paired_trades if t["profit"] > 0]
        losing_trades = [t for t in paired_trades if t["profit"] < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        avg_profit = float(np.mean([t["profit"] for t in winning_trades])) if winning_trades else 0.0
        avg_loss = float(np.mean([t["profit"] for t in losing_trades])) if losing_trades else 0.0

        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 4),
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_loss_ratio": round(profit_loss_ratio, 4)
        }

    def _pair_trades(
        self,
        buy_trades: List[Dict],
        sell_trades: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        使用FIFO（先进先出）算法配对买卖交易

        Args:
            buy_trades: 买入交易列表
            sell_trades: 卖出交易列表

        Returns:
            配对后的交易列表
        """
        paired = []
        buy_queue = []  # 买入队列（每个元素为 {trade, remaining_shares}）

        # 按日期排序
        buy_trades = sorted(buy_trades, key=lambda x: x["date"])
        sell_trades = sorted(sell_trades, key=lambda x: x["date"])

        # 初始化买入队列
        for buy_trade in buy_trades:
            buy_queue.append({
                "trade": buy_trade,
                "remaining_shares": buy_trade["shares"]
            })

        # 处理每笔卖出交易
        for sell_trade in sell_trades:
            remaining_shares_to_sell = sell_trade["shares"]

            while remaining_shares_to_sell > 0 and buy_queue:
                buy_entry = buy_queue[0]
                buy_trade = buy_entry["trade"]
                buy_shares_available = buy_entry["remaining_shares"]

                # 计算本次配对数量
                paired_shares = min(remaining_shares_to_sell, buy_shares_available)

                # 计算盈亏
                # 方法: 价差盈亏 - 手续费
                profit = (sell_trade["price"] - buy_trade["price"]) * paired_shares

                # 计算手续费(不包含成交金额)
                # 买入的total_cost包含amount,需要减去amount得到纯手续费
                buy_cost_ratio = paired_shares / buy_trade["shares"]
                buy_fees = (buy_trade["total_cost"] - buy_trade["amount"]) * buy_cost_ratio

                # 卖出的total_cost本身就是纯手续费(不包含amount)
                sell_cost_ratio = paired_shares / sell_trade["shares"]
                sell_fees = sell_trade["total_cost"] * sell_cost_ratio

                profit -= (buy_fees + sell_fees)

                # 记录手续费(用于显示)
                buy_cost = buy_fees
                sell_cost = sell_fees

                paired.append({
                    "buy_date": buy_trade["date"],
                    "sell_date": sell_trade["date"],
                    "buy_price": buy_trade["price"],
                    "sell_price": sell_trade["price"],
                    "shares": paired_shares,
                    "profit": profit,
                    "buy_cost": buy_cost,
                    "sell_cost": sell_cost
                })

                # 更新队列
                if paired_shares >= buy_shares_available:
                    # 完全消耗了这个买入批次
                    buy_queue.pop(0)
                else:
                    # 部分消耗了这个买入批次
                    buy_entry["remaining_shares"] -= paired_shares

                remaining_shares_to_sell -= paired_shares

        return paired

    def _calculate_equity_curve(self, daily_states: List[Dict]) -> Dict[str, Any]:
        """
        计算资金曲线

        Args:
            daily_states: 每日状态列表

        Returns:
            资金曲线数据字典
        """
        # 数据验证
        if not daily_states:
            logger.warning("每日状态数据为空，返回空资金曲线")
            return {
                "dates": [],
                "total_assets": [],
                "cash": [],
                "position_value": []
            }

        # 验证必需字段
        required_fields = ["date", "total_assets", "cash", "market_value"]
        for i, state in enumerate(daily_states):
            missing_fields = [f for f in required_fields if f not in state]
            if missing_fields:
                raise ValueError(
                    f"每日状态数据缺少必要字段: 索引={i}, 缺少字段={missing_fields}"
                )

        dates = [state["date"] for state in daily_states]
        total_assets = [state["total_assets"] for state in daily_states]
        cash = [state["cash"] for state in daily_states]
        position_value = [state["market_value"] for state in daily_states]

        return {
            "dates": dates,
            "total_assets": total_assets,
            "cash": cash,
            "position_value": position_value
        }


# ===================== 依赖注入 =====================

_result_calculator_service = None


def get_result_calculator_service() -> ResultCalculator:
    """获取结果计算器服务实例"""
    global _result_calculator_service
    if _result_calculator_service is None:
        from app.core.database import get_mongo_db
        db = get_mongo_db()
        _result_calculator_service = ResultCalculator(db)
    return _result_calculator_service
