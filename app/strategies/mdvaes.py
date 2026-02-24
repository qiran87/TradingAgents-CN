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

        # 多锚点权重配置（从前端传入的 anchor_weight 参数中获取）
        anchor_weight = self.get_parameter("anchor_weight", None)
        if anchor_weight:
            # 前端传入的是字典格式: {"peg": 0.4, "pe_historical": 0.3, "pb": 0.15, "dcf": 0.15}
            self.anchor_weight = anchor_weight
        else:
            # 使用默认权重
            self.anchor_weight = {"peg": 0.4, "pe_historical": 0.3, "pb": 0.15, "dcf": 0.15}

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

    def _build_valuation_metadata(self, valuation) -> Dict[str, Any]:
        """构建估值元数据

        从估值结果中提取完整的元数据，包括各个估值方法的值和 EPS
        """
        metadata = {
            "intrinsic_value": float(valuation.intrinsic_value),
            "lower_bound": float(valuation.lower_bound),
            "upper_bound": float(valuation.upper_bound),
            "confidence": float(valuation.confidence)
        }

        # 从 valuation_method 字典中提取各个估值方法的值
        if hasattr(valuation, 'valuation_method') and valuation.valuation_method:
            metadata["peg_value"] = float(valuation.valuation_method.get("peg", 0))
            metadata["pe_value"] = float(valuation.valuation_method.get("pe_historical", 0))
            metadata["pb_value"] = float(valuation.valuation_method.get("pb", 0))
            metadata["dcf_value"] = float(valuation.valuation_method.get("dcf", 0))
            metadata["valuation_method"] = valuation.valuation_method

        # 存储 EPS（回测阶段计算时使用的 EPS）
        # 确保 eps 字段始终存在于 metadata 中
        if hasattr(valuation, 'eps') and valuation.eps is not None:
            try:
                metadata["eps"] = float(valuation.eps)
            except (TypeError, ValueError) as e:
                import logging
                logging.warning(f"⚠️ 无法转换 EPS 值: {valuation.eps}, 错误: {e}")
                metadata["eps"] = 0.0
        else:
            # 如果没有 eps，记录警告并设置为 0
            import logging
            logging.warning(f"⚠️ 估值对象缺少 EPS 字段: hasattr={hasattr(valuation, 'eps')}")
            metadata["eps"] = 0.0

        return metadata

    def _calculate_valuation(self, timestamp: datetime, current_price: float) -> Dict[str, Any]:
        """计算估值（使用同步方法）

        关键技术点：
        - on_bar 是同步方法，直接使用同步方法获取数据
        - 使用 pymongo 同步客户端，避免事件循环问题
        """
        date_str = timestamp.strftime("%Y-%m-%d")
        try:
            # 1. 构建 MDVAES 参数（包含 anchor_weight）
            params_kwargs = {
                "forecast_years": self.forecast_years,
                "peg_base": self.peg_base,
                "risk_adjustment": self.risk_adjustment,
                "signal_mode": "safety_margin" if self.use_margin else "valuation_range",
                "safety_margin_buy": self.margin_buy,
                "safety_margin_sell": self.margin_sell,
                "anchor_weight": self.anchor_weight  # 使用从前端传入的权重
            }
            params = MDVAESParams(**params_kwargs)
            params.validate()

            # 2. 获取 EPS 预测（使用同步方法）
            eps_forecasts = self.data_reader.get_eps_forecast_sync(
                self.symbol, date_str, self.forecast_years
            )

            # 3. 计算增长指标
            growth_metrics = self.growth_calculator.calculate(eps_forecasts)

            # 4. 获取当前 EPS（使用最新预测值）
            current_eps = eps_forecasts[0].eps_forecast

            # 5. 获取当前 PE（使用同步方法）
            current_pe = self.data_reader.get_current_pe_sync(self.symbol, date_str)
            current_pe = current_pe if current_pe else 15.0  # 默认15倍

            # 6. 获取国债利率（使用同步方法）
            bond_rate = self.data_reader.get_bond_rate_sync(date_str)

            # 7. 获取每股自由现金流（使用同步方法）
            current_fcfps = self.data_reader.get_current_fcfps_sync(self.symbol, date_str)

            # 8. 构建风险指标（简化版，实际应从财务数据计算）
            risk_metrics = RiskMetrics(
                debt_to_assets=0.5,
                current_ratio=1.5,
                quick_ratio=1.2,
                cashflow_to_income=1.1,
                risk_level=RiskLevel.MEDIUM
            )

            # 9. 计算估值（如果存在 fcfps 则使用，否则使用 eps）
            valuation_result = self.valuation_calculator.calculate(
                growth_metrics=growth_metrics,
                risk_metrics=risk_metrics,
                eps=current_eps,
                current_pe=current_pe,
                bond_rate=bond_rate,
                params=params,
                fcfps=current_fcfps
            )

            return {
                "success": True,
                "valuation": valuation_result,
                "growth_metrics": growth_metrics,
                "eps_forecasts": eps_forecasts,
                "current_eps": current_eps,
                "current_fcfps": current_fcfps,
                "current_pe": current_pe,
                "bond_rate": bond_rate,
                "used_fcfps": current_fcfps is not None  # 标记是否使用了 FCFPS
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
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

        # 根据当前价格动态生成交易信号
        # 使用估值区间来判断买卖时机
        if self.use_margin:
            # 使用安全边际模式
            buy_threshold = valuation.intrinsic_value * self.margin_buy
            sell_threshold = valuation.intrinsic_value * self.margin_sell

            if current_price <= buy_threshold and position == 0:
                # 价格低于买入阈值，且无持仓 -> 买入
                buy_amount = int((cash * 0.9) / current_price / 100) * 100
                if buy_amount > 0:
                    return {
                        "action": "buy",
                        "amount": buy_amount,
                        "reason": (
                            f"估值买入: 内在价值={valuation.intrinsic_value:.2f}, "
                            f"买入阈值={buy_threshold:.2f}, "
                            f"价格={current_price:.2f}, "
                            f"安全边际={(1 - current_price/valuation.intrinsic_value)*100:.1f}%"
                        ),
                        "metadata": self._build_valuation_metadata(valuation)
                    }

            elif current_price >= sell_threshold and position > 0:
                # 价格高于卖出阈值，且有持仓 -> 卖出
                return {
                    "action": "sell",
                    "amount": position,
                    "reason": (
                        f"估值卖出: 内在价值={valuation.intrinsic_value:.2f}, "
                        f"卖出阈值={sell_threshold:.2f}, "
                        f"价格={current_price:.2f}, "
                        f"高估={(current_price/valuation.intrinsic_value - 1)*100:.1f}%"
                    ),
                    "metadata": self._build_valuation_metadata(valuation)
                }
        else:
            # 使用估值区间模式
            if current_price < valuation.lower_bound and position == 0:
                # 价格低于下限，且无持仓 -> 买入
                buy_amount = int((cash * 0.9) / current_price / 100) * 100
                if buy_amount > 0:
                    return {
                        "action": "buy",
                        "amount": buy_amount,
                        "reason": (
                            f"估值买入: 内在价值={valuation.intrinsic_value:.2f}, "
                            f"下限={valuation.lower_bound:.2f}, "
                            f"价格={current_price:.2f}, "
                            f"低估={(valuation.lower_bound - current_price)/valuation.lower_bound*100:.1f}%"
                        ),
                        "metadata": self._build_valuation_metadata(valuation)
                    }

            elif current_price > valuation.upper_bound and position > 0:
                # 价格高于上限，且有持仓 -> 卖出
                return {
                    "action": "sell",
                    "amount": position,
                    "reason": (
                        f"估值卖出: 内在价值={valuation.intrinsic_value:.2f}, "
                        f"上限={valuation.upper_bound:.2f}, "
                        f"价格={current_price:.2f}, "
                        f"高估={(current_price - valuation.upper_bound)/valuation.upper_bound*100:.1f}%"
                    ),
                    "metadata": self._build_valuation_metadata(valuation)
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
            "metadata": self._build_valuation_metadata(valuation)
        }
