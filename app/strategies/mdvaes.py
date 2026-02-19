"""MDVAES 估值策略

基于多锚点估值系统(MDVAES)进行价值投资决策。
通过分析师盈利预测、历史数据外推、多锚点估值(PEG/PE/PB/DCF)计算内在价值，
当价格低于内在价值下限时买入，高于上限时卖出。
"""
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from app.strategies.base import BaseStrategy
from app.domain.mdvaes import MDVAESParams, RiskMetrics, RiskLevel, SignalType
from app.services.mdvaes_data_reader import MDVAESDataReader
from app.services.growth_calculator import GrowthCalculator
from app.services.valuation_calculator import ValuationCalculator


class MDVAESStrategy(BaseStrategy):
    """MDVAES 估值策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        # 策略参数
        self.symbol = self.get_parameter("symbol", "000001.SZ")
        self.forecast_years = self.get_parameter("forecast_years", 5)
        self.peg_base = self.get_parameter("peg_base", 1.0)
        self.risk_adjustment = self.get_parameter("risk_adjustment", 0.1)
        self.rebalance_frequency = self.get_parameter("rebalance_frequency", 90)  # 天数
        self.use_margin = self.get_parameter("use_margin", True)
        self.margin_buy = self.get_parameter("margin_buy", 0.8)
        self.margin_sell = self.get_parameter("margin_sell", 1.2)

        # 内部状态
        self.data_reader = MDVAESDataReader()
        self.growth_calculator = GrowthCalculator()
        self.valuation_calculator = ValuationCalculator()

        # 缓存
        self.last_valuation = None
        self.last_valuation_date = None
        self.bar_count = 0

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "symbol",
                "type": "str",
                "default_value": "000001.SZ",
                "description": "股票代码",
                "required": True
            },
            {
                "name": "forecast_years",
                "type": "int",
                "default_value": 5,
                "range": {"min": 1, "max": 10},
                "description": "EPS预测年数",
                "required": False
            },
            {
                "name": "peg_base",
                "type": "float",
                "default_value": 1.0,
                "range": {"min": 0.5, "max": 2.0},
                "description": "PEG基数",
                "required": False
            },
            {
                "name": "risk_adjustment",
                "type": "float",
                "default_value": 0.1,
                "range": {"min": 0.0, "max": 0.3},
                "description": "风险调整幅度",
                "required": False
            },
            {
                "name": "rebalance_frequency",
                "type": "int",
                "default_value": 90,
                "range": {"min": 1, "max": 365},
                "description": "重新估值频率(天)",
                "required": False
            },
            {
                "name": "use_margin",
                "type": "bool",
                "default_value": True,
                "description": "使用安全边际",
                "required": False
            },
            {
                "name": "margin_buy",
                "type": "float",
                "default_value": 0.8,
                "range": {"min": 0.5, "max": 0.95},
                "description": "买入安全边际(价格低于估值的百分比)",
                "required": False
            },
            {
                "name": "margin_sell",
                "type": "float",
                "default_value": 1.2,
                "range": {"min": 1.05, "max": 2.0},
                "description": "卖出安全边际(价格高于估值的百分比)",
                "required": False
            }
        ]

    def get_strategy_id(self) -> str:
        return "mdvaes"

    def get_strategy_name(self) -> str:
        return "MDVAES估值策略"

    def get_strategy_description(self) -> str:
        return """基于多锚点估值系统(MDVAES)进行价值投资决策。

核心逻辑：
1. 获取分析师盈利预测或历史EPS外推
2. 使用对数最小二乘法计算增长率
3. 多锚点估值：PEG、历史PE、PB、DCF加权
4. 风险调整后得到内在价值区间
5. 价格低于下限时买入，高于上限时卖出

特点：
- 价值投资导向，适合长期持有
- 结合基本面数据和技术面信号
- 动态安全边际保护
"""

    def get_strategy_category(self) -> str:
        return "valuation"  # 估值类策略

    def _should_revaluate(self, timestamp: datetime) -> bool:
        """判断是否需要重新估值"""
        if self.last_valuation is None:
            return True

        days_since_last = (timestamp - self.last_valuation_date).days
        return days_since_last >= self.rebalance_frequency

    def _calculate_valuation(self, timestamp: datetime, current_price: float) -> Dict[str, Any]:
        """计算估值（同步包装异步方法）"""
        try:
            # 使用 asyncio.run 在同步上下文中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            date_str = timestamp.strftime("%Y-%m-%d")

            # 1. 构建 MDVAES 参数
            params = MDVAESParams(
                forecast_years=self.forecast_years,
                peg_base=self.peg_base,
                risk_adjustment=self.risk_adjustment,
                signal_mode="safety_margin" if self.use_margin else "valuation_range",
                safety_margin_buy=self.margin_buy,
                safety_margin_sell=self.margin_sell
            )
            params.validate()

            # 2. 获取 EPS 预测
            eps_forecasts = loop.run_until_complete(
                self.data_reader.get_eps_forecast(
                    self.symbol, date_str, self.forecast_years
                )
            )

            # 3. 计算增长指标
            growth_metrics = self.growth_calculator.calculate(eps_forecasts)

            # 4. 获取当前 EPS（使用最新预测值）
            current_eps = eps_forecasts[0].eps_forecast

            # 5. 获取当前 PE
            db = loop.run_until_complete(self.data_reader.get_current_pe(
                loop.run_until_complete(self.data_reader.get_mongo_db()),
                self.symbol,
                date_str
            ))
            current_pe = db if db else 15.0  # 默认15倍

            # 6. 获取国债利率
            bond_rate = loop.run_until_complete(
                self.data_reader.get_bond_rate(date_str)
            )

            # 7. 构建风险指标（简化版，实际应从财务数据计算）
            risk_metrics = RiskMetrics(
                debt_to_assets=0.5,
                current_ratio=1.5,
                quick_ratio=1.2,
                cashflow_to_income=1.1,
                risk_level=RiskLevel.MEDIUM
            )

            # 8. 计算估值
            valuation_result = self.valuation_calculator.calculate(
                growth_metrics=growth_metrics,
                risk_metrics=risk_metrics,
                eps=current_eps,
                current_pe=current_pe,
                bond_rate=bond_rate,
                params=params
            )

            loop.close()

            return {
                "success": True,
                "valuation": valuation_result,
                "growth_metrics": growth_metrics,
                "eps_forecasts": eps_forecasts,
                "current_pe": current_pe,
                "bond_rate": bond_rate
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback_valuation": self.last_valuation
            }

    def on_bar(
        self,
        bar_id: str,
        timestamp: datetime,
        current_price: float,
        position: int,
        cash: float
    ) -> Dict[str, Any]:
        """
        处理单个K线数据

        注意：由于估值基于基本面数据，不需要每次都重新计算。
        按照rebalance_frequency频率重新估值。

        Args:
            bar_id: K线ID
            timestamp: 时间戳
            current_price: 当前价格
            position: 当前持仓（股数）
            cash: 当前现金

        Returns:
            交易信号
        """
        self.bar_count += 1

        # 首次运行或达到重新估值频率
        if self._should_revaluate(timestamp):
            result = self._calculate_valuation(timestamp, current_price)

            if result["success"]:
                self.last_valuation = result["valuation"]
                self.last_valuation_date = timestamp
            elif result.get("fallback_valuation"):
                # 使用上次估值
                self.last_valuation = result["fallback_valuation"]

        # 如果没有估值，保持观望
        if self.last_valuation is None:
            return {"action": "hold", "amount": 0, "reason": "估值计算中，保持观望"}

        valuation = self.last_valuation
        signal = valuation.signal

        # 根据信号执行交易
        if signal == SignalType.BUY and position == 0:
            # 买入信号，无持仓
            buy_amount = int((cash * 0.9) / current_price / 100) * 100
            if buy_amount > 0:
                return {
                    "action": "buy",
                    "amount": buy_amount,
                    "reason": (
                        f"估值买入: 内在价值={valuation.intrinsic_value:.2f}, "
                        f"下限={valuation.lower_bound:.2f}, "
                        f"价格={current_price:.2f}, "
                        f"安全边际={(1 - current_price/valuation.intrinsic_value)*100:.1f}%"
                    ),
                    "metadata": {
                        "intrinsic_value": valuation.intrinsic_value,
                        "lower_bound": valuation.lower_bound,
                        "upper_bound": valuation.upper_bound,
                        "confidence": valuation.confidence,
                        "valuation_method": valuation.valuation_method
                    }
                }

        elif signal == SignalType.SELL and position > 0:
            # 卖出信号，有持仓
            return {
                "action": "sell",
                "amount": position,
                "reason": (
                    f"估值卖出: 内在价值={valuation.intrinsic_value:.2f}, "
                    f"上限={valuation.upper_bound:.2f}, "
                    f"价格={current_price:.2f}, "
                    f"高估={(current_price/valuation.intrinsic_value - 1)*100:.1f}%"
                ),
                "metadata": {
                    "intrinsic_value": valuation.intrinsic_value,
                    "lower_bound": valuation.lower_bound,
                    "upper_bound": valuation.upper_bound,
                    "confidence": valuation.confidence
                }
            }

        # 持有或无操作
        return {
            "action": "hold",
            "amount": 0,
            "reason": (
                f"估值持有: 内在价值={valuation.intrinsic_value:.2f}, "
                f"区间=[{valuation.lower_bound:.2f}, {valuation.upper_bound:.2f}], "
                f"价格={current_price:.2f}"
            ),
            "metadata": {
                "intrinsic_value": valuation.intrinsic_value,
                "lower_bound": valuation.lower_bound,
                "upper_bound": valuation.upper_bound,
                "confidence": valuation.confidence
            }
        }
