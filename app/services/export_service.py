"""
回测结果导出服务
负责生成Excel文件、PDF文件等
"""
import io
from typing import Dict, List, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from fastapi import Depends

from tradingagents.utils.logging_init import get_logger
from app.core.database import get_mongo_db

logger = get_logger(__name__)


class ExcelExporter:
    """Excel导出器"""

    def __init__(self):
        """初始化导出器"""
        self.styles = {
            "title": Font(size=16, bold=True, color="FFFFFF"),
            "subtitle": Font(size=14, bold=True, color="4472C4"),
            "header": Font(bold=True, color="FFFFFF"),
            "label": Font(bold=True),
            "normal": Font(size=11),
            "percentage": Font(size=11),
            "number": Font(size=11)
        }
        self.fills = {
            "title": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
            "header": PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid"),
            "subtitle": PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"),
            "alternate": PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        }
        self.borders = {
            "thin": Border(
                left=Side(style='thin', color='D0D0D0'),
                right=Side(style='thin', color='D0D0D0'),
                top=Side(style='thin', color='D0D0D0'),
                bottom=Side(style='thin', color='D0D0D0')
            )
        }
        self.alignments = {
            "left": Alignment(horizontal='left', vertical='center', wrap_text=True),
            "center": Alignment(horizontal='center', vertical='center', wrap_text=True),
            "right": Alignment(horizontal='right', vertical='center', wrap_text=False)
        }

    def export_backtest_results(
        self,
        backtest_id: str,
        history_record: Optional[Dict],
        results: Dict,
        trades: List[Dict],
        equity_curve: Dict
    ) -> bytes:
        """
        导出完整回测结果到Excel（标准3个工作表格式）

        Args:
            backtest_id: 回测ID
            history_record: 历史记录（可选）
            results: 回测结果
            trades: 交易明细列表
            equity_curve: 资金曲线数据（暂不使用，保留接口兼容性）

        Returns:
            Excel文件的二进制数据
        """
        logger.info(f"📊 开始生成Excel文件（标准3表格式）: {backtest_id}")

        try:
            wb = Workbook()
            wb.remove(wb.active)

            # ✅ P2-3: 创建3个标准工作表
            # 1. 回测参数
            self._create_parameters_sheet(wb, backtest_id, history_record, results)

            # 2. 核心结果
            self._create_core_results_sheet(wb, results)

            # 3. 交易明细
            self._create_trades_sheet(wb, trades)

            # 保存到内存
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            excel_bytes = output.read()
            output.close()

            logger.info(f"✅ Excel文件生成成功（3个标准工作表）: {len(excel_bytes)} bytes")
            return excel_bytes

        except Exception as e:
            logger.error(f"❌ 生成Excel文件失败: {e}", exc_info=True)
            raise

    def _create_summary_sheet(
        self,
        wb: Workbook,
        backtest_id: str,
        history_record: Optional[Dict],
        results: Dict
    ):
        """创建摘要工作表"""
        ws = wb.create_sheet("回测摘要", 0)

        # 标题行
        ws['A1'] = "回测结果摘要报告"
        ws['A1'].font = self.styles["title"]
        ws['A1'].fill = self.fills["title"]
        ws['A1'].alignment = self.alignments["center"]
        ws.merge_cells('A1:D1')
        ws.row_dimensions[1].height = 30

        # 生成时间
        ws['A2'] = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A2'].font = Font(size=10, italic=True, color="808080")
        ws.merge_cells('A2:D2')

        row = 4

        # 基本信息
        if history_record:
            ws[f'A{row}'] = "基本信息"
            ws[f'A{row}'].font = self.styles["subtitle"]
            ws[f'A{row}'].fill = self.fills["subtitle"]
            ws.merge_cells(f'A{row}:D{row}')
            row += 2

            # 记录名称
            self._add_label_value(ws, row, "记录名称", history_record.get("name", ""))
            row += 1

            # 描述
            description = history_record.get("description", "")
            if description:
                self._add_label_value(ws, row, "描述", description)
                row += 1

            # 标签
            tags = history_record.get("tags", [])
            if tags:
                self._add_label_value(ws, row, "标签", ", ".join(tags))
                row += 1

        # 参数信息
        parameters = history_record.get("parameters", {}) if history_record else {}
        if parameters:
            ws[f'A{row}'] = "回测参数"
            ws[f'A{row}'].font = self.styles["subtitle"]
            ws[f'A{row}'].fill = self.fills["subtitle"]
            ws.merge_cells(f'A{row}:D{row}')
            row += 2

            self._add_label_value(ws, row, "股票代码", parameters.get("stock_code", ""))
            row += 1

            self._add_label_value(ws, row, "回测期间",
                                f"{parameters.get('start_date', '')} ~ {parameters.get('end_date', '')}")
            row += 1

            self._add_label_value(ws, row, "初始资金",
                                f"¥{parameters.get('initial_capital', 0):,.2f}")
            row += 1

            self._add_label_value(ws, row, "策略", parameters.get("strategy_id", ""))
            row += 2

        # 关键指标
        metrics_snapshot = history_record.get("metrics_snapshot", {}) if history_record else {}
        if not metrics_snapshot and "metrics_snapshot" in results:
            metrics_snapshot = results["metrics_snapshot"]

        if metrics_snapshot:
            ws[f'A{row}'] = "关键指标"
            ws[f'A{row}'].font = self.styles["subtitle"]
            ws[f'A{row}'].fill = self.fills["subtitle"]
            ws.merge_cells(f'A{row}:D{row}')
            row += 2

            self._add_label_value(ws, row, "总收益率",
                                f"{metrics_snapshot.get('total_return', 0)*100:.2f}%",
                                is_percentage=True)
            row += 1

            self._add_label_value(ws, row, "最大回撤",
                                f"{metrics_snapshot.get('max_drawdown', 0)*100:.2f}%",
                                is_percentage=True)
            row += 1

            self._add_label_value(ws, row, "夏普比率",
                                f"{metrics_snapshot.get('sharpe_ratio', 0):.4f}")
            row += 1

            self._add_label_value(ws, row, "胜率",
                                f"{metrics_snapshot.get('win_rate', 0)*100:.2f}%",
                                is_percentage=True)
            row += 1

            self._add_label_value(ws, row, "交易次数",
                                str(metrics_snapshot.get('total_trades', 0)))

        # 设置列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15

        # 冻结首行
        ws.freeze_panes = 'A4'

    def _create_parameters_sheet(
        self,
        wb: Workbook,
        backtest_id: str,
        history_record: Optional[Dict],
        results: Dict
    ):
        """
        ✅ P2-3: 创建"回测参数"标准工作表

        包含：
        - 基本信息（记录名称、描述、标签）
        - 回测参数（股票代码、日期范围、初始资金、策略等）
        """
        ws = wb.create_sheet("回测参数", 0)

        # 标题行
        ws['A1'] = "回测参数配置"
        ws['A1'].font = self.styles["title"]
        ws['A1'].fill = self.fills["title"]
        ws['A1'].alignment = self.alignments["center"]
        ws.merge_cells('A1:D1')
        ws.row_dimensions[1].height = 30

        # 生成时间和回测ID
        ws['A2'] = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  回测ID: {backtest_id}"
        ws['A2'].font = Font(size=10, italic=True, color="808080")
        ws.merge_cells('A2:D2')

        row = 4

        # ========== 基本信息 ==========
        if history_record:
            ws[f'A{row}'] = "基本信息"
            ws[f'A{row}'].font = self.styles["subtitle"]
            ws[f'A{row}'].fill = self.fills["subtitle"]
            ws.merge_cells(f'A{row}:D{row}')
            row += 2

            # 记录名称
            self._add_label_value(ws, row, "记录名称", history_record.get("name", ""))
            row += 1

            # 描述
            description = history_record.get("description", "")
            if description:
                self._add_label_value(ws, row, "描述", description)
                row += 1

            # 标签
            tags = history_record.get("tags", [])
            if tags:
                self._add_label_value(ws, row, "标签", ", ".join(tags))
                row += 1

            # 创建时间
            created_at = history_record.get("created_at")
            if created_at:
                created_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(created_at, datetime) else str(created_at)
                self._add_label_value(ws, row, "创建时间", created_str)
                row += 2
            else:
                row += 1

        # ========== 回测参数 ==========
        ws[f'A{row}'] = "回测参数配置"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:D{row}')
        row += 2

        parameters = history_record.get("parameters", {}) if history_record else {}

        # 股票信息
        self._add_label_value(ws, row, "股票代码", parameters.get("stock_code", ""))
        row += 1

        self._add_label_value(ws, row, "股票名称", parameters.get("stock_name", ""))
        row += 1

        # 回测期间
        start_date = parameters.get("start_date", "")
        end_date = parameters.get("end_date", "")
        self._add_label_value(ws, row, "回测期间", f"{start_date} ~ {end_date}")
        row += 1

        # 初始资金
        initial_capital = parameters.get("initial_capital", 0)
        self._add_label_value(ws, row, "初始资金", f"¥{initial_capital:,.2f}")
        row += 1

        # 策略信息
        strategy_id = parameters.get("strategy_id", "")
        strategy_name = {
            "dual_ma": "双均线策略",
            "buy_and_hold": "买入持有策略"
        }.get(strategy_id, strategy_id)
        self._add_label_value(ws, row, "使用策略", strategy_name)
        row += 1

        # 策略参数（如果有）
        if strategy_id == "dual_ma":
            short_window = parameters.get("short_window", 5)
            long_window = parameters.get("long_window", 20)
            self._add_label_value(ws, row, "短期均线", f"{short_window}日")
            row += 1
            self._add_label_value(ws, row, "长期均线", f"{long_window}日")
            row += 2
        else:
            row += 1

        # ========== 其他参数 ==========
        ws[f'A{row}'] = "其他参数"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:D{row}')
        row += 2

        # 最小购买量
        min_purchase = parameters.get("min_purchase", 100)
        self._add_label_value(ws, row, "最小购买量", f"{min_purchase}股")
        row += 1

        # 交易手续费
        commission_rate = parameters.get("commission_rate", 0.0003)
        stamp_duty_rate = parameters.get("stamp_duty_rate", 0.001)
        self._add_label_value(ws, row, "佣金费率", f"{commission_rate*100:.3f}%")
        row += 1
        self._add_label_value(ws, row, "印花税率", f"{stamp_duty_rate*100:.2f}%")
        row += 1

        # 设置列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15

        # 冻结首行
        ws.freeze_panes = 'A4'

    def _create_core_results_sheet(self, wb: Workbook, results: Dict):
        """
        ✅ P2-3: 创建"核心结果"标准工作表

        包含：
        - 关键指标摘要
        - 收益指标
        - 风险指标
        - 风险调整收益指标
        - 交易统计
        """
        ws = wb.create_sheet("核心结果", 1)

        row = 1

        # ========== 关键指标摘要 ==========
        metrics_snapshot = results.get("metrics_snapshot", {})
        if metrics_snapshot:
            ws[f'A{row}'] = "关键指标摘要"
            ws[f'A{row}'].font = self.styles["subtitle"]
            ws[f'A{row}'].fill = self.fills["subtitle"]
            ws.merge_cells(f'A{row}:B{row}')
            row += 2

            self._add_metric_row(ws, row, "总收益率", metrics_snapshot.get('total_return', 0))
            row += 1
            self._add_metric_row(ws, row, "最大回撤", metrics_snapshot.get('max_drawdown', 0))
            row += 1
            self._add_metric_row(ws, row, "夏普比率", metrics_snapshot.get('sharpe_ratio', 0), is_ratio=True)
            row += 1
            self._add_metric_row(ws, row, "胜率", metrics_snapshot.get('win_rate', 0))
            row += 1
            self._add_metric_row(ws, row, "交易次数", metrics_snapshot.get('total_trades', 0), is_integer=True)
            row += 2

        # ========== 收益指标 ==========
        ws[f'A{row}'] = "收益指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        return_metrics = results.get("return_metrics", {})
        if return_metrics:
            self._add_metric_row(ws, row, "总收益率", return_metrics.get('total_return', 0))
            row += 1
            self._add_metric_row(ws, row, "年化收益率", return_metrics.get('annual_return', 0))
            row += 1
            self._add_metric_row(ws, row, "累计收益", return_metrics.get('cumulative_return', 0))
            row += 1

            final_equity = return_metrics.get('final_equity', 0)
            if final_equity > 0:
                self._add_label_value(ws, row, "最终资金", f"¥{final_equity:,.2f}")
                row += 1

            total_profit = return_metrics.get('total_profit', 0)
            if total_profit != 0:
                self._add_label_value(ws, row, "总盈亏", f"¥{total_profit:,.2f}")
                color = "00B050" if total_profit > 0 else "FF0000"
                ws[f'B{row}'].font = Font(size=11, bold=True, color=color)
                row += 1
        else:
            row += 5

        # ========== 风险指标 ==========
        ws[f'A{row}'] = "风险指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        risk_metrics = results.get("risk_metrics", {})
        if risk_metrics:
            self._add_metric_row(ws, row, "最大回撤", risk_metrics.get('max_drawdown', 0))
            row += 1
            self._add_metric_row(ws, row, "平均回撤", risk_metrics.get('avg_drawdown', 0))
            row += 1
            self._add_metric_row(ws, row, "波动率", risk_metrics.get('volatility', 0))
            row += 1
            self._add_metric_row(ws, row, "下行风险", risk_metrics.get('downside_risk', 0))
            row += 1
            self._add_metric_row(ws, row, "VaAR (95%)", risk_metrics.get('var_95', 0))
            row += 2
        else:
            row += 6

        # ========== 风险调整收益指标 ==========
        ws[f'A{row}'] = "风险调整收益指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        risk_adjusted_metrics = results.get("risk_adjusted_metrics", {})
        if risk_adjusted_metrics:
            self._add_metric_row(ws, row, "夏普比率", risk_adjusted_metrics.get('sharpe_ratio', 0), is_ratio=True)
            row += 1
            self._add_metric_row(ws, row, "索提诺比率", risk_adjusted_metrics.get('sortino_ratio', 0), is_ratio=True)
            row += 1
            self._add_metric_row(ws, row, "卡尔玛比率", risk_adjusted_metrics.get('calmar_ratio', 0), is_ratio=True)
            row += 1
            self._add_metric_row(ws, row, "信息比率", risk_adjusted_metrics.get('information_ratio', 0), is_ratio=True)
            row += 2
        else:
            row += 5

        # ========== 交易统计 ==========
        ws[f'A{row}'] = "交易统计"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        trading_stats = results.get("trading_stats", {})
        if trading_stats:
            self._add_metric_row(ws, row, "总交易次数", trading_stats.get('total_trades', 0), is_integer=True)
            row += 1
            self._add_metric_row(ws, row, "盈利次数", trading_stats.get('winning_trades', 0), is_integer=True)
            row += 1
            self._add_metric_row(ws, row, "亏损次数", trading_stats.get('losing_trades', 0), is_integer=True)
            row += 1
            self._add_metric_row(ws, row, "胜率", trading_stats.get('win_rate', 0))
            row += 1
            self._add_metric_row(ws, row, "盈亏比", trading_stats.get('profit_loss_ratio', 0))
            row += 1

            avg_profit = trading_stats.get('avg_profit', 0)
            if avg_profit != 0:
                self._add_label_value(ws, row, "平均盈利", f"¥{avg_profit:,.2f}")
                row += 1

            avg_loss = trading_stats.get('avg_loss', 0)
            if avg_loss != 0:
                self._add_label_value(ws, row, "平均亏损", f"¥{avg_loss:,.2f}")
                row += 1

            largest_win = trading_stats.get('largest_win', 0)
            if largest_win != 0:
                self._add_label_value(ws, row, "最大盈利", f"¥{largest_win:,.2f}")
                row += 1

            largest_loss = trading_stats.get('largest_loss', 0)
            if largest_loss != 0:
                self._add_label_value(ws, row, "最大亏损", f"¥{largest_loss:,.2f}")
                row += 1

            avg_hold_days = trading_stats.get('avg_hold_days', 0)
            if avg_hold_days > 0:
                self._add_label_value(ws, row, "平均持仓天数", f"{avg_hold_days:.1f}天")
                row += 1

        # 设置列宽
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 30

        # 冻结首行
        ws.freeze_panes = 'A2'

    def _create_metrics_sheet(self, wb: Workbook, results: Dict):
        """创建详细指标工作表"""
        ws = wb.create_sheet("详细指标", 1)

        row = 1

        # 收益指标
        ws[f'A{row}'] = "收益指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        return_metrics = results.get("return_metrics", {})
        if return_metrics:
            self._add_metric_row(ws, row, "总收益率", return_metrics.get('total_return', 0))
            row += 1
            self._add_metric_row(ws, row, "年化收益率", return_metrics.get('annual_return', 0))
            row += 2

        # 风险指标
        ws[f'A{row}'] = "风险指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        risk_metrics = results.get("risk_metrics", {})
        if risk_metrics:
            self._add_metric_row(ws, row, "最大回撤", risk_metrics.get('max_drawdown', 0))
            row += 1
            self._add_metric_row(ws, row, "波动率", risk_metrics.get('volatility', 0))
            row += 1
            self._add_metric_row(ws, row, "下行波动率", risk_metrics.get('downside_volatility', 0))
            row += 1
            self._add_metric_row(ws, row, "VaR (95%)", risk_metrics.get('var_95', 0))
            row += 2

        # 风险调整收益指标
        ws[f'A{row}'] = "风险调整收益指标"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        ra_metrics = results.get("risk_adjusted_metrics", {})
        if ra_metrics:
            self._add_metric_row(ws, row, "夏普比率", ra_metrics.get('sharpe_ratio', 0))
            row += 1
            self._add_metric_row(ws, row, "索提诺比率", ra_metrics.get('sortino_ratio', 0))
            row += 1
            self._add_metric_row(ws, row, "卡玛比率", ra_metrics.get('calmar_ratio', 0))
            row += 2

        # 交易统计
        ws[f'A{row}'] = "交易统计"
        ws[f'A{row}'].font = self.styles["subtitle"]
        ws[f'A{row}'].fill = self.fills["subtitle"]
        ws.merge_cells(f'A{row}:B{row}')
        row += 2

        trading_stats = results.get("trading_stats", {})
        if trading_stats:
            self._add_label_value(ws, row, "总交易次数", str(trading_stats.get('total_trades', 0)))
            row += 1
            self._add_label_value(ws, row, "盈利交易", str(trading_stats.get('winning_trades', 0)))
            row += 1
            self._add_label_value(ws, row, "亏损交易", str(trading_stats.get('losing_trades', 0)))
            row += 1
            self._add_label_value(ws, row, "胜率",
                                f"{trading_stats.get('win_rate', 0)*100:.2f}%")
            row += 1
            self._add_label_value(ws, row, "平均盈利",
                                f"¥{trading_stats.get('avg_profit', 0):,.2f}")
            row += 1
            self._add_label_value(ws, row, "平均亏损",
                                f"¥{trading_stats.get('avg_loss', 0):,.2f}")
            row += 1
            self._add_label_value(ws, row, "盈亏比",
                                f"{trading_stats.get('profit_loss_ratio', 0):.2f}")

        # 设置列宽
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 25

    def _create_trades_sheet(self, wb: Workbook, trades: List[Dict]):
        """创建交易明细工作表"""
        ws = wb.create_sheet("交易明细", 2)

        # 表头
        headers = ["日期", "类型", "价格", "股数", "金额", "佣金", "印花税", "总费用", "现金后", "持仓后"]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = self.styles["header"]
            cell.fill = self.fills["header"]
            cell.alignment = self.alignments["center"]
            cell.border = self.borders["thin"]

        ws.row_dimensions[1].height = 25

        # 数据行
        for row_idx, trade in enumerate(trades, 2):
            date = trade.get("date", "")
            trade_type = "买入" if trade.get("trade_type") == "buy" else "卖出"
            price = trade.get("price", 0)
            shares = trade.get("shares", 0)
            amount = trade.get("amount", 0)
            commission = trade.get("commission", 0)
            stamp_duty = trade.get("stamp_duty", 0)
            total_cost = trade.get("total_cost", 0)
            cash_after = trade.get("cash_after", 0)
            position_after = trade.get("position_after", 0)

            # 写入数据
            data = [
                date, trade_type, price, shares, amount,
                commission, stamp_duty, total_cost, cash_after, position_after
            ]

            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.value = value
                cell.font = self.styles["normal"]
                cell.alignment = self.alignments["right"] if col >= 3 else self.alignments["center"]
                cell.border = self.borders["thin"]

                # 隔行变色
                if row_idx % 2 == 0:
                    cell.fill = self.fills["alternate"]

            # 交易类型列左对齐
            ws.cell(row=row_idx, column=2).alignment = self.alignments["center"]
            # 日期列居中
            ws.cell(row=row_idx, column=1).alignment = self.alignments["center"]

        # 设置列宽
        column_widths = [15, 10, 15, 12, 15, 12, 12, 12, 15, 15]
        for col_idx, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # 冻结首行
        ws.freeze_panes = 'A2'

    def _create_equity_curve_sheet(self, wb: Workbook, equity_curve: Dict):
        """创建资金曲线工作表"""
        ws = wb.create_sheet("资金曲线", 3)

        # 表头
        headers = ["日期", "总资产", "现金", "持仓市值"]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = self.styles["header"]
            cell.fill = self.fills["header"]
            cell.alignment = self.alignments["center"]
            cell.border = self.borders["thin"]

        ws.row_dimensions[1].height = 25

        # 数据行
        dates = equity_curve.get("dates", [])
        total_assets = equity_curve.get("total_assets", [])
        cash = equity_curve.get("cash", [])
        position_value = equity_curve.get("position_value", [])

        for row_idx, (date, assets, cash_val, position) in enumerate(
            zip(dates, total_assets, cash, position_value), 2
        ):
            data = [date, assets, cash_val, position]

            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.value = value
                cell.font = self.styles["normal"]
                cell.alignment = self.alignments["right"] if col > 1 else self.alignments["center"]
                cell.border = self.borders["thin"]

                # 隔行变色
                if row_idx % 2 == 0:
                    cell.fill = self.fills["alternate"]

        # 设置列宽
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 18

        # 冻结首行
        ws.freeze_panes = 'A2'

    def _add_label_value(
        self,
        ws,
        row: int,
        label: str,
        value: str,
        is_percentage: bool = False
    ):
        """添加标签-值对"""
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = self.styles["label"]
        ws[f'A{row}'].alignment = self.alignments["left"]

        ws[f'B{row}'] = value
        ws[f'B{row}'].font = self.styles["percentage"] if is_percentage else self.styles["number"]
        ws[f'B{row}'].alignment = self.alignments["left"]

        # 添加边框
        ws[f'A{row}'].border = self.borders["thin"]
        ws[f'B{row}'].border = self.borders["thin"]

    def _add_metric_row(self, ws, row: int, label: str, value: float):
        """添加指标行"""
        is_percentage = "率" in label or "回撤" in label or "收益" in label

        ws[f'A{row}'] = label
        ws[f'A{row}'].font = self.styles["label"]
        ws[f'A{row}'].alignment = self.alignments["left"]
        ws[f'A{row}'].border = self.borders["thin"]

        if is_percentage:
            ws[f'B{row}'] = f"{value*100:.4f}%"
        else:
            ws[f'B{row}'] = f"{value:.4f}"

        ws[f'B{row}'].font = self.styles["percentage"]
        ws[f'B{row}'].alignment = self.alignments["right"]
        ws[f'B{row}'].border = self.borders["thin"]


class ExportService:
    """导出服务"""

    def __init__(self, db):
        """
        初始化导出服务

        Args:
            db: MongoDB数据库实例
        """
        self.db = db
        self.excel_exporter = ExcelExporter()

    async def export_backtest_to_excel(
        self,
        backtest_id: str,
        user_id: str = "default"
    ) -> tuple[bytes, str]:
        """
        导出回测结果为Excel文件

        Args:
            backtest_id: 回测ID
            user_id: 用户ID

        Returns:
            (Excel文件的二进制数据, 文件名)

        Raises:
            BacktestResultNotFoundError: 回测结果不存在
        """
        logger.info(f"📥 开始导出回测结果: {backtest_id}")

        try:
            # 1. 获取历史记录（如果存在）
            history_record = await self.db.backtest_history.find_one({
                "backtest_id": backtest_id,
                "user_id": user_id
            })

            # 2. 获取回测结果
            results = await self.db.backtest_results.find_one({
                "backtest_id": backtest_id
            })

            if not results:
                logger.error(f"❌ 回测结果不存在: {backtest_id}")
                raise BacktestResultNotFoundError(f"回测结果不存在: {backtest_id}")

            # 3. 获取交易明细
            trades_cursor = self.db.backtest_trades.find({
                "backtest_id": backtest_id
            }).sort("date", 1)

            trades = await trades_cursor.to_list(length=None)

            # 4. 获取资金曲线
            equity_curve = results.get("equity_curve", {})

            # 5. 生成Excel文件
            excel_bytes = self.excel_exporter.export_backtest_results(
                backtest_id=backtest_id,
                history_record=history_record,
                results=results,
                trades=trades,
                equity_curve=equity_curve
            )

            # 6. 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_{backtest_id}_{timestamp}.xlsx"

            logger.info(f"✅ 导出成功: {filename}")
            return excel_bytes, filename

        except BacktestResultNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 导出回测结果失败: {e}", exc_info=True)
            raise ExportServiceError(f"导出回测结果失败: {str(e)}")


# ===================== 异常类 =====================

class ExportServiceError(Exception):
    """导出服务异常"""
    pass


class BacktestResultNotFoundError(ExportServiceError):
    """回测结果不存在异常"""
    pass


# ===================== 服务工厂函数 =====================

_export_service_instance: Optional[ExportService] = None


def get_export_service(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> ExportService:
    """
    获取导出服务实例

    Args:
        db: MongoDB数据库实例（依赖注入）

    Returns:
        ExportService实例
    """
    return ExportService(db)
