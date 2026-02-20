# MDVAES 估值模型实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现基于基本面分析的多维度价值锚定评估系统（MDVAES），支持估值计算、可视化展示和历史回测。

**架构:** 采用 DDD 分层架构，从数据层向上实现：MongoDB 集合 → 数据读取服务 → 核心计算逻辑 → 策略实现 → API 路由 → 前端组件。复用现有 BacktestEngine 和 BaseStrategy，扩展 Tushare 数据同步。

**技术栈:**
- 后端: FastAPI, Motor (MongoDB 异步), APScheduler, Tushare Pro
- 前端: Vue 3, TypeScript, Pinia, ECharts, Element Plus
- 数据库: MongoDB (7 个新集合), Redis (缓存)

---

## 实施前准备

### Task 0: 创建工作分支和验证环境

**Files:**
- Git branch: `strategy_mdvaes` (已存在)

**Step 1: 验证当前分支**

```bash
git branch --show-current
```

Expected: `strategy_mdvaes`

**Step 2: 检查 Python 环境**

```bash
cd backend
python --version
```

Expected: `Python 3.11.x`

**Step 3: 检查依赖安装**

```bash
pip list | grep -E "(fastapi|motor|pymongo)"
```

Expected: fastapi, motor, pymongo 已安装

**Step 4: 检查 Tushare Token**

```bash
grep TUSHARE_TOKEN .env
```

Expected: `TUSHARE_TOKEN=xxxxx` (非空)

**Step 5: 验证 MongoDB 连接**

```bash
python -c "from app.core.database import get_mongo_db; import asyncio; asyncio.run(get_mongo_db())"
```

Expected: 无错误

---

## Phase 1: 数据层 - MongoDB 集合和索引

### Task 1.1: 创建 MongoDB 集合初始化脚本

**Files:**
- Create: `app/scripts/init_mdvaes_db.py`

**Step 1: 创建初始化脚本文件**

```python
# app/scripts/init_mdvaes_db.py
"""初始化 MDVAES 相关的 MongoDB 集合和索引"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def create_mdvaes_collections():
    """创建 MDVAES 集合和索引"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    try:
        # 1. 分析师盈利预测
        await db.mdvaes_analyst_forecasts.create_index([
            ("ts_code", 1),
            ("quarter", 1),
            ("report_date", -1)
        ])
        print("✅ mdvaes_analyst_forecasts 索引创建完成")

        # 2. EPS 历史数据
        await db.mdvaes_eps_history.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_eps_history 索引创建完成")

        # 3. PE 历史数据
        await db.mdvaes_pe_history.create_index([
            ("ts_code", 1),
            ("trade_date", -1)
        ])
        print("✅ mdvaes_pe_history 索引创建完成")

        # 4. 现金流数据
        await db.mdvaes_cashflow_data.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_cashflow_data 索引创建完成")

        # 5. 财务比率
        await db.mdvaes_financial_ratios.create_index([
            ("ts_code", 1),
            ("end_date", -1)
        ])
        print("✅ mdvaes_financial_ratios 索引创建完成")

        # 6. 国债收益率
        await db.mdvaes_bond_rate.create_index([
            ("trade_date", -1),
            ("curve_term", 1)
        ])
        print("✅ mdvaes_bond_rate 索引创建完成")

        # 7. 估值缓存
        await db.mdvaes_valuation_cache.create_index([
            ("ts_code", 1),
            ("calculation_date", -1),
            ("params_hash", 1)
        ])
        print("✅ mdvaes_valuation_cache 索引创建完成")

        print("\n🎉 所有 MDVAES 集合和索引创建完成！")

    except Exception as e:
        print(f"❌ 创建索引失败: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(create_mdvaes_collections())
```

**Step 2: 运行初始化脚本**

```bash
python -m app.scripts.init_mdvaes_db
```

Expected: 输出 7 个 "✅" 消息

**Step 3: 验证集合创建**

```bash
mongosh mongodb://admin:password@localhost:27017/tradingagents --eval "db.getCollectionNames()"
```

Expected: 输出包含 `mdvaes_analyst_forecasts` 等 7 个集合

**Step 4: 提交**

```bash
git add app/scripts/init_mdvaes_db.py
git commit -m "feat(mdvaes): add MongoDB collections initialization script"
```

---

## Phase 2: 数据同步服务

### Task 2.1: 创建 MDVAES 数据同步服务

**Files:**
- Create: `app/services/mdvaes_data_sync_service.py`

**Step 1: 创建数据同步服务文件**

```python
# app/services/mdvaes_data_sync_service.py
"""MDVAES 数据同步服务 - 从 Tushare 同步数据到 MongoDB"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import tushare as ts
from app.core.config import settings
from app.core.database import get_mongo_db

logger = logging.getLogger(__name__)


class MDVAESDataSyncService:
    """MDVAES 数据同步服务"""

    def __init__(self):
        self.pro = ts.pro_api(settings.TUSHARE_TOKEN)

    async def sync_daily_data(self, trade_date: str):
        """同步指定交易日的所有 MDVAES 数据"""
        logger.info(f"开始同步 MDVAES 数据: {trade_date}")

        db = await get_mongo_db()

        try:
            # 1. 同步分析师盈利预测（使用最近报告日期）
            await self._sync_analyst_forecasts(db, trade_date)

            # 2. 同步每日基本面数据（包含 PE、PB）
            await self._sync_daily_basic(db, trade_date)

            # 3. 同步国债收益率
            await self._sync_bond_yield(db, trade_date)

            logger.info(f"✅ MDVAES 数据同步完成: {trade_date}")
            return {
                "success": True,
                "trade_date": trade_date,
                "synced_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ MDVAES 数据同步失败: {e}", exc_info=True)
            raise

    async def _sync_analyst_forecasts(self, db, report_date: str):
        """同步分析师盈利预测

        Tushare 接口: report_rc (doc_id=292)
        """
        all_forecasts = []
        offset = 0
        limit = 3000

        while True:
            df = self.pro.report_rc(
                report_date=report_date,
                offset=offset,
                limit=limit
            )

            if df.empty:
                break

            # 转换为字典列表
            records = df.to_dict('records')
            all_forecasts.extend(records)

            offset += limit
            if len(df) < limit:
                break

        if all_forecasts:
            # 批量插入（使用 upsert 避免重复）
            for record in all_forecasts:
                await db.mdvaes_analyst_forecasts.update_one(
                    {
                        "ts_code": record["ts_code"],
                        "quarter": record["quarter"],
                        "report_date": record["report_date"]
                    },
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

            logger.info(f"  ✅ 同步分析师预测: {len(all_forecasts)} 条")

    async def _sync_daily_basic(self, db, trade_date: str):
        """同步每日基本面数据（PE、PB 等）

        Tushare 接口: daily_basic (doc_id=32)
        """
        # 获取前 10 个交易日（确保数据完整性）
        start_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=20)).strftime("%Y%m%d")

        df = self.pro.daily_basic(
            ts_code="",
            start_date=start_date,
            end_date=trade_date,
            fields="ts_code,trade_date,pe,pe_ttm,pb,ps"
        )

        if not df.empty:
            records = df.to_dict('records')

            # 批量插入
            for record in records:
                await db.mdvaes_pe_history.update_one(
                    {
                        "ts_code": record["ts_code"],
                        "trade_date": record["trade_date"]
                    },
                    {
                        "$set": {
                            **record,
                            "synced_at": datetime.now()
                        }
                    },
                    upsert=True
                )

            logger.info(f"  ✅ 同步每日基本面: {len(records)} 条")

    async def _sync_bond_yield(self, db, trade_date: str):
        """同步国债收益率

        Tushare 接口: yc_cb (doc_id=201)
        获取 10 年期国债收益率
        """
        df = self.pro.yc_cb(
            ts_code="1001.CB",  # 国债代码
            curve_type="0",      # 到期收益率
            curve_term=10.0,     # 10 年期
            start_date=trade_date,
            end_date=trade_date
        )

        if not df.empty:
            record = df.iloc[0].to_dict()

            await db.mdvaes_bond_rate.update_one(
                {
                    "trade_date": trade_date,
                    "curve_term": 10.0
                },
                {
                    "$set": {
                        **record,
                        "synced_at": datetime.now()
                    }
                },
                upsert=True
            )

            logger.info(f"  ✅ 同步国债收益率: {record['yield']}%")
```

**Step 2: 创建测试文件**

```python
# tests/services/test_mdvaes_data_sync_service.py
import pytest
from app.services.mdvaes_data_sync_service import MDVAESDataSyncService

@pytest.mark.asyncio
class TestMDVAESDataSyncService:
    """MDVAES 数据同步服务测试"""

    @pytest.fixture
    def service(self):
        return MDVAESDataSyncService()

    def test_init(self, service):
        """测试初始化"""
        assert service.pro is not None
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/services/test_mdvaes_data_sync_service.py -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add app/services/mdvaes_data_sync_service.py tests/services/test_mdvaes_data_sync_service.py
git commit -m "feat(mdvaes): add data sync service from Tushare"
```

---

### Task 2.2: 创建数据同步 Worker

**Files:**
- Create: `app/worker/mdvaes_sync_worker.py`

**Step 1: 创建 Worker 文件**

```python
# app/worker/mdvaes_sync_worker.py
"""MDVAES 数据同步 Worker"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.mdvaes_data_sync_service import MDVAESDataSyncService
from app.services.trading_calendar_service import TradingCalendarService

logger = logging.getLogger(__name__)

# 创建调度器
scheduler = AsyncIOScheduler()

# 数据同步服务
sync_service = MDVAESDataSyncService()
calendar_service = TradingCalendarService()


async def daily_sync_task():
    """每日数据同步任务（每个交易日 16:30 执行）"""
    try:
        # 获取最新交易日
        latest_trade_date = await calendar_service.get_latest_trading_day()
        trade_date_str = latest_trade_date.strftime("%Y%m%d")

        # 执行同步
        result = await sync_service.sync_daily_data(trade_date_str)
        logger.info(f"MDVAES 每日同步完成: {result}")

    except Exception as e:
        logger.error(f"MDVAES 每日同步失败: {e}", exc_info=True)


# 配置定时任务
scheduler.add_job(
    daily_sync_task,
    'cron',
    hour=16,
    minute=30,
    id='mdvaes_daily_sync',
    name='MDVAES 每日数据同步'
)


async def main():
    """启动 Worker"""
    logger.info("MDVAES 数据同步 Worker 启动")
    scheduler.start()

    try:
        # 保持运行
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
        scheduler.shutdown()
        logger.info("MDVAES 数据同步 Worker 已停止")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: 更新 docker-compose.yml 添加 Worker 服务**

```yaml
# 在 docker-compose.yml 中添加
  mdvaes-worker:
    build: ./backend
    command: python -m app.worker.mdvaes_sync_worker
    environment:
      - MONGODB_HOST=mongodb
      - REDIS_HOST=redis
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
    depends_on:
      - mongodb
      - redis
    restart: unless-stopped
```

**Step 3: 提交**

```bash
git add app/worker/mdvaes_sync_worker.py docker-compose.yml
git commit -m "feat(mdvaes): add data sync worker with APScheduler"
```

---

## Phase 3: 核心计算逻辑

### Task 3.1: 创建 DDD 领域模型

**Files:**
- Create: `app/domain/mdvaes.py`

**Step 1: 创建领域模型文件**

```python
# app/domain/mdvaes.py
"""MDVAES 领域模型"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """交易信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TrendStability(str, Enum):
    """趋势稳定性"""
    STABLE = "stable"
    VOLATILE = "volatile"
    DECLINING = "declining"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class EPSForecast:
    """EPS 预测（实体）"""
    year: int
    eps_forecast: float
    forecast_date: str
    analyst_count: int
    source: str  # "analyst" or "historical_extrapolation"


@dataclass(frozen=True)
class GrowthMetrics:
    """增长指标（值对象）"""
    cagr: float  # 复合年均增长率
    growth_rate: float  # 增长率
    r_squared: float  # R² 拟合优度
    growth_quality_score: float  # 增长质量评分 (0-1)
    trend_stability: TrendStability  # 趋势稳定性


@dataclass(frozen=True)
class RiskMetrics:
    """风险指标（值对象）"""
    debt_to_assets: float  # 资产负债率
    current_ratio: float  # 流动比率
    quick_ratio: float  # 速动比率
    cashflow_to_income: float  # 现金流/利润比率
    risk_level: RiskLevel  # 风险等级


@dataclass(frozen=True)
class ValuationResult:
    """估值结果（值对象）"""
    intrinsic_value: float  # 内在价值
    lower_bound: float  # 估值下限
    upper_bound: float  # 估值上限
    confidence: float  # 置信度 (0-1)
    valuation_method: Dict[str, float]  # 各方法估值
    signal: SignalType  # 交易信号


@dataclass(frozen=True)
class MDVAESParams:
    """MDVAES 参数（值对象）"""
    # 预测参数
    forecast_years: int = 5
    min_forecast_count: int = 3

    # 估值参数
    peg_base: float = 1.0
    peg_interest_sensitivity: float = 0.5
    risk_adjustment: float = 0.1

    # 多锚点权重
    anchor_weight: Dict[str, float] = field(default_factory=lambda: {
        "peg": 0.4,
        "pe_historical": 0.3,
        "pb": 0.15,
        "dcf": 0.15
    })

    # 信号参数
    signal_mode: str = "valuation_range"  # or "safety_margin"
    safety_margin_buy: float = 0.8
    safety_margin_sell: float = 1.2

    # 预设标识
    preset: Optional[str] = None  # conservative/neutral/aggressive

    def validate(self):
        """验证参数"""
        if not 1 <= self.forecast_years <= 10:
            raise ValueError("forecast_years 必须在 1-10 之间")
        if not 0.5 <= self.peg_base <= 2.0:
            raise ValueError("peg_base 必须在 0.5-2.0 之间")
        if not 0 <= self.risk_adjustment <= 0.3:
            raise ValueError("risk_adjustment 必须在 0-0.3 之间")
        if self.signal_mode not in ["valuation_range", "safety_margin"]:
            raise ValueError("signal_mode 必须是 valuation_range 或 safety_margin")

        # 验证权重总和
        total_weight = sum(self.anchor_weight.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"anchor_weight 总和必须为 1.0，当前为 {total_weight}")
```

**Step 2: 创建领域模型测试**

```python
# tests/domain/test_mdvaes.py
import pytest
from app.domain.mdvaes import (
    MDVAESParams, GrowthMetrics, RiskMetrics, ValuationResult,
    SignalType, TrendStability, RiskLevel
)

class TestMDVAESParams:
    """MDVAES 参数测试"""

    def test_default_params(self):
        """测试默认参数"""
        params = MDVAESParams()
        assert params.forecast_years == 5
        assert params.peg_base == 1.0
        assert params.signal_mode == "valuation_range"

    def test_validate_success(self):
        """测试参数验证成功"""
        params = MDVAESParams(
            forecast_years=5,
            peg_base=1.0,
            anchor_weight={"peg": 0.5, "pe_historical": 0.5, "pb": 0.0, "dcf": 0.0}
        )
        params.validate()  # 不应该抛出异常

    def test_validate_fail_forecast_years(self):
        """测试预测年数验证失败"""
        params = MDVAESParams(forecast_years=15)
        with pytest.raises(ValueError, match="forecast_years"):
            params.validate()

    def test_validate_fail_weight_sum(self):
        """测试权重总和验证失败"""
        params = MDVAESParams(
            anchor_weight={"peg": 0.5, "pe_historical": 0.6, "pb": 0.0, "dcf": 0.0}
        )
        with pytest.raises(ValueError, match="总和必须为 1.0"):
            params.validate()
```

**Step 3: 运行测试**

```bash
pytest tests/domain/test_mdvaes.py -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add app/domain/mdvaes.py tests/domain/test_mdvaes.py
git commit -m "feat(mdvaes): add domain models with validation"
```

---

### Task 3.2: 创建核心计算器

**Files:**
- Create: `app/services/mdvaes_calculator.py`
- Create: `app/services/growth_calculator.py`
- Create: `app/services/valuation_calculator.py`

**Step 1: 创建增长率计算器**

```python
# app/services/growth_calculator.py
"""增长率计算器"""

import numpy as np
from typing import List
from app.domain.mdvaes import EPSForecast, GrowthMetrics, TrendStability


class GrowthCalculator:
    """增长指标计算器"""

    @staticmethod
    def calculate(eps_forecasts: List[EPSForecast]) -> GrowthMetrics:
        """计算增长指标

        使用对数最小二乘法回归分析 EPS 增长率
        """
        if len(eps_forecasts) < 2:
            raise ValueError("至少需要 2 个 EPS 预测数据点")

        # 提取年份和 EPS
        years = np.array([f.year for f in eps_forecasts])
        eps_values = np.array([f.eps_forecast for f in eps_forecasts])

        # 过滤掉非正数 EPS
        valid_mask = eps_values > 0
        if not valid_mask.any():
            raise ValueError("所有 EPS 值都必须为正数")

        years = years[valid_mask]
        eps_values = eps_values[valid_mask]

        # 对数最小二乘法回归
        log_eps = np.log(eps_values)
        coeffs = np.polyfit(years, log_eps, 1)
        slope = coeffs[0]
        intercept = coeffs[1]

        # 计算 R²
        log_eps_pred = np.polyval(coeffs, years)
        ss_res = np.sum((log_eps - log_eps_pred) ** 2)
        ss_tot = np.sum((log_eps - np.mean(log_eps)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 计算 CAGR (复合年均增长率)
        n_years = years[-1] - years[0]
        if n_years > 0:
            cagr = (eps_values[-1] / eps_values[0]) ** (1 / n_years) - 1
        else:
            cagr = 0

        # 增长率（基于斜率）
        growth_rate = np.exp(slope) - 1

        # 增长质量评分（基于 R² 和增长一致性）
        growth_quality_score = min(r_squared, 0.95)  # 最高 0.95

        # 趋势稳定性
        if r_squared >= 0.8:
            trend_stability = TrendStability.STABLE
        elif r_squared >= 0.5:
            trend_stability = TrendStability.VOLATILE
        else:
            trend_stability = TrendStability.DECLINING

        return GrowthMetrics(
            cagr=cagr,
            growth_rate=growth_rate,
            r_squared=r_squared,
            growth_quality_score=growth_quality_score,
            trend_stability=trend_stability
        )
```

**Step 2: 创建估值计算器**

```python
# app/services/valuation_calculator.py
"""估值计算器"""

from typing import Dict
from app.domain.mdvaes import GrowthMetrics, RiskMetrics, ValuationResult, MDVAESParams


class ValuationCalculator:
    """估值计算器"""

    @staticmethod
    def calculate(
        growth_metrics: GrowthMetrics,
        risk_metrics: RiskMetrics,
        eps: float,
        current_pe: float,
        bond_rate: float,
        params: MDVAESParams
    ) -> ValuationResult:
        """计算多锚点估值

        Args:
            growth_metrics: 增长指标
            risk_metrics: 风险指标
            eps: 当前 EPS
            current_pe: 当前 PE
            bond_rate: 无风险利率（10年期国债收益率）
            params: MDVAES 参数

        Returns:
            ValuationResult: 估值结果
        """
        # 1. PEG 估值
        peg_valuation = ValuationCalculator._calc_peg_valuation(
            eps, growth_metrics, bond_rate, params
        )

        # 2. 历史 PE 估值
        pe_historical_valuation = ValuationCalculator._calc_pe_historical_valuation(
            eps, current_pe, growth_metrics
        )

        # 3. PB 估值（简化版，使用固定倍数）
        pb_valuation = eps * 1.5  # 简化：假设 PB = 1.5

        # 4. DCF 估值（简化版）
        dcf_valuation = ValuationCalculator._calc_dcf_valuation(
            eps, growth_metrics.growth_rate, bond_rate, params
        )

        # 5. 多锚点加权
        weighted_valuation = (
            params.anchor_weight["peg"] * peg_valuation +
            params.anchor_weight["pe_historical"] * pe_historical_valuation +
            params.anchor_weight["pb"] * pb_valuation +
            params.anchor_weight["dcf"] * dcf_valuation
        )

        # 6. 风险调整
        risk_adjustment_factor = ValuationCalculator._get_risk_adjustment_factor(
            risk_metrics.risk_level
        )
        adjusted_valuation = weighted_valuation * (1 - params.risk_adjustment * risk_adjustment_factor)

        # 7. 计算估值区间
        confidence = ValuationCalculator._calc_confidence(growth_metrics, risk_metrics)
        margin = adjusted_valuation * (1 - confidence) * 0.2  # 置信度越低，区间越宽

        lower_bound = adjusted_valuation - margin
        upper_bound = adjusted_valuation + margin

        # 8. 生成交易信号
        signal = ValuationCalculator._generate_signal(
            adjusted_valuation, lower_bound, upper_bound, params
        )

        return ValuationResult(
            intrinsic_value=adjusted_valuation,
            lower_bound=max(lower_bound, 0),
            upper_bound=upper_bound,
            confidence=confidence,
            valuation_method={
                "peg": peg_valuation,
                "pe_historical": pe_historical_valuation,
                "pb": pb_valuation,
                "dcf": dcf_valuation
            },
            signal=signal
        )

    @staticmethod
    def _calc_peg_valuation(
        eps: float,
        growth_metrics: GrowthMetrics,
        bond_rate: float,
        params: MDVAESParams
    ) -> float:
        """计算 PEG 估值

        PEG = PE / (增长率 * 100)
        估值 = EPS * PEG 基础值 * (1 + 增长率) * 利率调整
        """
        # 宏观利率联动：利率越高，PEG 越低
        interest_adjustment = 1 - params.peg_interest_sensitivity * bond_rate
        peg_valuation = eps * growth_metrics.growth_rate * params.peg_base * interest_adjustment
        return max(peg_valuation, 0)

    @staticmethod
    def _calc_pe_historical_valuation(
        eps: float,
        current_pe: float,
        growth_metrics: GrowthMetrics
    ) -> float:
        """基于历史 PE 估值"""
        # 使用历史 PE 倍数，考虑增长率调整
        growth_adjustment = 1 + growth_metrics.growth_rate
        pe_historical_valuation = eps * current_pe * growth_adjustment * 0.8  # 保守系数
        return max(pe_historical_valuation, 0)

    @staticmethod
    def _calc_dcf_valuation(
        eps: float,
        growth_rate: float,
        discount_rate: float,
        params: MDVAESParams
    ) -> float:
        """简化 DCF 估值"""
        # 永续增长模型
        terminal_growth = 0.03  # 终端增长率 3%
        required_return = discount_rate + 0.05  # 要求回报率 = 无风险利率 + 风险溢价

        if growth_rate >= required_return:
            # 增长率过高，使用保守估计
            growth_rate = required_return - 0.01

        # 预测期价值
        forecast_values = []
        for i in range(1, params.forecast_years + 1):
            forecast_eps = eps * ((1 + growth_rate) ** i)
            discounted_value = forecast_eps / ((1 + required_return) ** i)
            forecast_values.append(discounted_value)

        # 终值
        terminal_eps = eps * ((1 + growth_rate) ** params.forecast_years)
        terminal_value = terminal_eps * (1 + terminal_growth) / (required_return - terminal_growth)
        discounted_terminal = terminal_value / ((1 + required_return) ** params.forecast_years)

        dcf_valuation = sum(forecast_values) + discounted_terminal
        return max(dcf_valuation, 0)

    @staticmethod
    def _get_risk_adjustment_factor(risk_level: str) -> float:
        """获取风险调整系数"""
        risk_map = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5
        }
        return risk_map.get(risk_level, 1.0)

    @staticmethod
    def _calc_confidence(growth_metrics: GrowthMetrics, risk_metrics: RiskMetrics) -> float:
        """计算估值置信度"""
        # 基于 R² 和风险等级
        base_confidence = growth_metrics.r_squared

        risk_penalty = {
            "low": 0.0,
            "medium": 0.1,
            "high": 0.2
        }
        penalty = risk_penalty.get(risk_metrics.risk_level, 0.1)

        confidence = max(base_confidence - penalty, 0.3)
        return min(confidence, 0.95)

    @staticmethod
    def _generate_signal(
        intrinsic_value: float,
        lower_bound: float,
        upper_bound: float,
        params: MDVAESParams
    ) -> str:
        """生成交易信号"""
        if params.signal_mode == "valuation_range":
            if intrinsic_value < lower_bound:
                return "buy"
            elif intrinsic_value > upper_bound:
                return "sell"
            else:
                return "hold"
        else:  # safety_margin
            buy_threshold = intrinsic_value * params.safety_margin_buy
            sell_threshold = intrinsic_value * params.safety_margin_sell

            if intrinsic_value <= buy_threshold:
                return "buy"
            elif intrinsic_value >= sell_threshold:
                return "sell"
            else:
                return "hold"
```

**Step 3: 创建测试**

```python
# tests/services/test_valuation_calculator.py
import pytest
from app.services.valuation_calculator import ValuationCalculator
from app.domain.mdvaes import GrowthMetrics, RiskMetrics, MDVAESParams, RiskLevel

class TestValuationCalculator:
    """估值计算器测试"""

    @pytest.fixture
    def growth_metrics(self):
        return GrowthMetrics(
            cagr=0.15,
            growth_rate=0.12,
            r_squared=0.89,
            growth_quality_score=0.8,
            trend_stability="stable"
        )

    @pytest.fixture
    def risk_metrics(self):
        return RiskMetrics(
            debt_to_assets=0.6,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.LOW
        )

    @pytest.fixture
    def params(self):
        return MDVAESParams()

    def test_calculate(self, growth_metrics, risk_metrics, params):
        """测试估值计算"""
        result = ValuationCalculator.calculate(
            growth_metrics=growth_metrics,
            risk_metrics=risk_metrics,
            eps=2.5,
            current_pe=10.0,
            bond_rate=0.0275,
            params=params
        )

        assert result.intrinsic_value > 0
        assert result.lower_bound > 0
        assert result.upper_bound > result.intrinsic_value
        assert result.signal in ["buy", "sell", "hold"]
        assert 0 <= result.confidence <= 1

    def test_peg_valuation(self, growth_metrics, params):
        """测试 PEG 估值"""
        peg = ValuationCalculator._calc_peg_valuation(
            eps=2.5,
            growth_metrics=growth_metrics,
            bond_rate=0.0275,
            params=params
        )
        assert peg > 0
```

**Step 4: 运行测试**

```bash
pytest tests/services/test_valuation_calculator.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add app/services/growth_calculator.py app/services/valuation_calculator.py tests/services/
git commit -m "feat(mdvaes): add core valuation calculators with growth and risk analysis"
```

---

## Phase 4: 数据读取服务

### Task 4.1: 创建数据读取器

**Files:**
- Create: `app/services/mdvaes_data_reader.py`

**Step 1: 创建数据读取器**

```python
# app/services/mdvaes_data_reader.py
"""MDVAES 数据读取器"""

from typing import List, Optional
from datetime import datetime
from app.core.database import get_mongo_db
from app.domain.mdvaes import EPSForecast


class MDVAESDataReader:
    """MDVAES 数据读取器"""

    async def get_eps_forecast(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> List[EPSForecast]:
        """获取 EPS 预测数据

        优先使用分析师预测，不足时使用历史数据外推
        """
        db = await get_mongo_db()

        # 1. 尝试从分析师预测获取
        analyst_forecasts = await self._get_analyst_forecasts(
            db, symbol, calculation_date, forecast_years
        )

        if analyst_forecasts:
            return analyst_forecasts

        # 2. 如果分析师预测不足，使用历史 EPS 外推
        historical_eps = await self._get_historical_eps(db, symbol, calculation_date)
        if len(historical_eps) >= 2:
            return self._extrapolate_eps(historical_eps, forecast_years)

        raise ValueError(f"无法获取 {symbol} 的 EPS 数据")

    async def _get_analyst_forecasts(
        self,
        db,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> Optional[List[EPSForecast]]:
        """从分析师预测获取 EPS"""
        current_year = datetime.strptime(calculation_date, "%Y-%m-%d").year

        forecasts = await db.mdvaes_analyst_forecasts.find({
            "ts_code": symbol,
            "forecast_date": {"$lte": calculation_date},
            "year": {"$gte": current_year, "$lte": current_year + forecast_years}
        }).sort("forecast_date", -1).to_list(None)

        if not forecasts:
            return None

        # 按年份去重，取最新预测
        latest_by_year = {}
        for f in forecasts:
            year = f.get("year") or self._extract_year_from_quarter(f.get("quarter", ""))
            if year and (year not in latest_by_year or f["forecast_date"] > latest_by_year[year]["forecast_date"]):
                latest_by_year[year] = f

        return [
            EPSForecast(
                year=year,
                eps_forecast=f["eps"],
                forecast_date=f["forecast_date"],
                analyst_count=f.get("analyst_count", 1),
                source="analyst"
            )
            for year, f in sorted(latest_by_year.items())
        ]

    async def _get_historical_eps(self, db, symbol: str, calculation_date: str, limit: int = 10) -> List[dict]:
        """获取历史 EPS 数据"""
        historical_eps = await db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "end_date": {"$lte": calculation_date}
        }).sort("end_date", -1).limit(limit).to_list(None)

        return historical_eps or []

    def _extrapolate_eps(self, historical_eps: List[dict], forecast_years: int) -> List[EPSForecast]:
        """基于历史 EPS 外推预测"""
        # 简化实现：使用线性增长
        latest_eps = historical_eps[0]["eps"]
        oldest_eps = historical_eps[-1]["eps"]
        n_years = len(historical_eps)
        growth_rate = (latest_eps / oldest_eps) ** (1 / (n_years - 1)) - 1 if n_years > 1 else 0.1

        base_year = datetime.strptime(historical_eps[0]["end_date"], "%Y-%m-%d").year

        forecasts = []
        for i in range(1, forecast_years + 1):
            forecast_eps = latest_eps * ((1 + growth_rate) ** i)
            forecasts.append(EPSForecast(
                year=base_year + i,
                eps_forecast=forecast_eps,
                forecast_date=datetime.now().strftime("%Y-%m-%d"),
                analyst_count=0,
                source="historical_extrapolation"
            ))

        return forecasts

    def _extract_year_from_quarter(self, quarter: str) -> Optional[int]:
        """从季度字符串提取年份"""
        try:
            # 格式: "2024Q4" -> 2024
            return int(quarter[:4])
        except (ValueError, IndexError):
            return None

    async def get_current_pe(self, db, symbol: str, calculation_date: str) -> Optional[float]:
        """获取当前 PE"""
        pe_data = await db.mdvaes_pe_history.find_one({
            "ts_code": symbol,
            "trade_date": {"$lte": calculation_date}
        }, sort=[("trade_date", -1)])

        return pe_data["pe_ttm"] if pe_data else None

    async def get_bond_rate(self, calculation_date: str) -> Optional[float]:
        """获取 10 年期国债收益率"""
        db = await get_mongo_db()

        bond_data = await db.mdvaes_bond_rate.find_one({
            "trade_date": {"$lte": calculation_date},
            "curve_term": 10.0
        }, sort=[("trade_date", -1)])

        if bond_data:
            # 返回收益率（百分数转为小数）
            return bond_data.get("yield", 0) / 100

        # 默认无风险利率 2.75%
        return 0.0275
```

**Step 2: 创建测试**

```python
# tests/services/test_mdvaes_data_reader.py
import pytest
from app.services.mdvaes_data_reader import MDVAESDataReader

@pytest.mark.asyncio
class TestMDVAESDataReader:
    """数据读取器测试"""

    @pytest.fixture
    def reader(self):
        return MDVAESDataReader()

    async def test_get_bond_rate(self, reader):
        """测试获取国债收益率"""
        rate = await reader.get_bond_rate("2024-01-15")
        assert rate is not None
        assert 0 <= rate <= 1
```

**Step 3: 运行测试**

```bash
pytest tests/services/test_mdvaes_data_reader.py -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add app/services/mdvaes_data_reader.py tests/services/test_mdvaes_data_reader.py
git commit -m "feat(mdvaes): add data reader for EPS, PE and bond rate"
```

---

## Phase 5: 策略实现

### Task 5.1: 创建 MDVAES 策略

**Files:**
- Create: `app/strategies/mdvaes.py`

**Step 1: 创建策略文件**

```python
# app/strategies/mdvaes.py
"""MDVAES 估值策略"""

from typing import Dict, Any
from app.strategies.base import BaseStrategy
from app.domain.mdvaes import MDVAESParams, SignalType
from app.services.mdvaes_calculator import ValuationCalculator
from app.services.mdvaes_data_reader import MDVAESDataReader


class MDVAESStrategy(BaseStrategy):
    """MDVAES 估值策略

    基于多维度价值锚定评估系统进行交易决策
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_reader = MDVAESDataReader()
        self.calculator = ValuationCalculator()

        # 当前估值结果缓存
        self._current_valuation = None
        self._valuation_date = None

    def get_parameters_definition(self) -> Dict[str, Any]:
        """获取参数定义"""
        return {
            "preset": {
                "type": "select",
                "label": "参数预设",
                "options": ["conservative", "neutral", "aggressive", "custom"],
                "default": "neutral",
                "description": "预设参数配置"
            },
            "signal_mode": {
                "type": "select",
                "label": "信号模式",
                "options": ["valuation_range", "safety_margin"],
                "default": "valuation_range",
                "description": "交易信号生成模式"
            },
            "forecast_years": {
                "type": "int",
                "label": "预测年数",
                "min": 1,
                "max": 10,
                "default": 5,
                "description": "EPS 预测年数"
            },
            "peg_base": {
                "type": "float",
                "label": "基础 PEG",
                "min": 0.5,
                "max": 2.0,
                "step": 0.1,
                "default": 1.0,
                "description": "PEG 估值的基础倍数"
            }
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        """验证参数"""
        # 如果使用预设，加载预设参数
        preset = params.get("preset")
        if preset and preset != "custom":
            # 预设参数验证可以放宽
            return

        # 自定义参数需要验证
        if "forecast_years" in params:
            if not 1 <= params["forecast_years"] <= 10:
                raise ValueError("forecast_years 必须在 1-10 之间")

        if "peg_base" in params:
            if not 0.5 <= params["peg_base"] <= 2.0:
                raise ValueError("peg_base 必须在 0.5-2.0 之间")

    async def on_bar(
        self,
        bar_id: str,
        timestamp: str,
        current_price: float,
        position: int,
        cash: float
    ) -> Dict[str, Any]:
        """处理单个 K 线数据，返回交易信号

        Args:
            bar_id: K 线 ID
            timestamp: 时间戳
            current_price: 当前价格
            position: 持仓数量
            cash: 可用现金

        Returns:
            交易信号字典
        """
        # 只在每个月末重新计算估值（避免频繁计算）
        if not self._should_revaluate(timestamp):
            return {"action": "hold"}

        # 获取参数
        params = MDVAESParams(**self.strategy_params)

        try:
            # 获取 EPS 预测
            eps_forecasts = await self.data_reader.get_eps_forecast(
                self.symbol,
                timestamp,
                params.forecast_years
            )

            # 获取当前 PE
            current_pe = await self.data_reader.get_current_pe(
                await self.data_reader.get_mongo_db(),
                self.symbol,
                timestamp
            )

            if not current_pe:
                return {"action": "hold", "reason": "无法获取 PE 数据"}

            # 获取国债利率
            bond_rate = await self.data_reader.get_bond_rate(timestamp)

            # 计算增长指标
            from app.services.growth_calculator import GrowthCalculator
            growth_metrics = GrowthCalculator.calculate(eps_forecasts)

            # 计算风险指标（简化版，使用固定值）
            from app.domain.mdvaes import RiskMetrics, RiskLevel
            risk_metrics = RiskMetrics(
                debt_to_assets=0.6,
                current_ratio=1.5,
                quick_ratio=1.2,
                cashflow_to_income=1.1,
                risk_level=RiskLevel.MEDIUM
            )

            # 计算估值
            # 获取最新 EPS
            latest_eps = eps_forecasts[0].eps_forecast
            valuation_result = self.calculator.calculate(
                growth_metrics=growth_metrics,
                risk_metrics=risk_metrics,
                eps=latest_eps,
                current_pe=current_pe,
                bond_rate=bond_rate,
                params=params
            )

            # 缓存估值结果
            self._current_valuation = valuation_result
            self._valuation_date = timestamp

            # 生成交易信号
            action = self._generate_action_from_signal(
                valuation_result.signal,
                current_price,
                position,
                cash
            )

            return {
                "action": action,
                "valuation": valuation_result.intrinsic_value,
                "lower_bound": valuation_result.lower_bound,
                "upper_bound": valuation_result.upper_bound,
                "signal": valuation_result.signal,
                "confidence": valuation_result.confidence
            }

        except Exception as e:
            # 计算失败，持有
            return {
                "action": "hold",
                "reason": f"估值计算失败: {str(e)}"
            }

    def _should_revaluate(self, timestamp: str) -> bool:
        """判断是否需要重新估值（每月末）"""
        from datetime import datetime
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        # 每月的最后一个交易日
        return dt.day >= 28  # 简化判断

    def _generate_action_from_signal(
        self,
        signal: SignalType,
        current_price: float,
        position: int,
        cash: float
    ) -> str:
        """根据信号生成交易动作"""
        if signal == SignalType.BUY:
            if position == 0 and cash > current_price * 100:  # 至少能买 1 手
                return "buy"
        elif signal == SignalType.SELL:
            if position > 0:
                return "sell"

        return "hold"
```

**Step 2: 注册策略**

```python
# app/strategies/__init__.py

from .mdvaes import MDVAESStrategy
```

**Step 3: 更新策略注册表**

```python
# app/strategies/registry.py

# 在 register_strategies 函数中添加
from app.strategies.mdvaes import MDVAESStrategy

def register_strategies():
    """注册所有策略"""
    registry.register("dual_ma", DualMAStrategy)
    registry.register("macd", MACDStrategy)
    registry.register("rsi", RSIStrategy)
    registry.register("bollinger_bands", BollingerBandsStrategy)
    registry.register("mdvaes", MDVAESStrategy)  # 新增
```

**Step 4: 创建测试**

```python
# tests/strategies/test_mdvaes_strategy.py
import pytest
from app.strategies.mdvaes import MDVAESStrategy

class TestMDVAESStrategy:
    """MDVAES 策略测试"""

    @pytest.fixture
    def strategy(self):
        return MDVAESStrategy(
            symbol="000001.SZ",
            strategy_params={"preset": "neutral"}
        )

    def test_get_parameters_definition(self, strategy):
        """测试参数定义"""
        params = strategy.get_parameters_definition()
        assert "preset" in params
        assert "signal_mode" in params

    def test_validate_params_valid(self, strategy):
        """测试参数验证成功"""
        strategy.validate_params({"preset": "neutral"})

    def test_validate_params_invalid(self, strategy):
        """测试参数验证失败"""
        with pytest.raises(ValueError):
            strategy.validate_params({"forecast_years": 15})
```

**Step 5: 运行测试**

```bash
pytest tests/strategies/test_mdvaes_strategy.py -v
```

Expected: PASS

**Step 6: 提交**

```bash
git add app/strategies/mdvaes.py app/strategies/__init__.py app/strategies/registry.py tests/strategies/test_mdvaes_strategy.py
git commit -m "feat(mdvaes): add MDVAES valuation strategy"
```

---

## Phase 6: API 路由实现

### Task 6.1: 创建 MDVAES API 路由

**Files:**
- Create: `app/routers/mdvaes.py`

**Step 1: 创建 API 路由文件**

```python
# app/routers/mdvaes.py
"""MDVAES 估值 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.core.response import ok, error
from app.core.database import get_mongo_db
from app.routers.auth_db import get_current_user
from app.services.mdvaes_calculator import ValuationCalculator
from app.services.mdvaes_data_reader import MDVAESDataReader
from app.services.growth_calculator import GrowthCalculator
from app.domain.mdvaes import MDVAESParams

router = APIRouter(prefix="/api/mdvaes", tags=["mdvaes"])


@router.post("/valuation")
async def get_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_mongo_db)
):
    """计算股票估值

    Args:
        request: 估值请求
        current_user: 当前用户
        db: MongoDB 数据库

    Returns:
        估值结果
    """
    try:
        # 验证用户权限
        check_subscription_tier(current_user, "mdvaes")

        # 构建参数对象
        params = MDVAESParams(**request.params)

        # 获取计算日期
        calculation_date = request.calculation_date or await get_latest_trading_date(db)

        # 获取数据
        data_reader = MDVAESDataReader()

        # 获取 EPS 预测
        eps_forecasts = await data_reader.get_eps_forecast(
            request.symbol,
            calculation_date,
            params.forecast_years
        )

        # 计算增长指标
        growth_metrics = GrowthCalculator.calculate(eps_forecasts)

        # 获取当前 PE
        current_pe = await data_reader.get_current_pe(db, request.symbol, calculation_date)
        if not current_pe:
            raise HTTPException(status_code=404, detail="无法获取 PE 数据")

        # 获取国债利率
        bond_rate = await data_reader.get_bond_rate(calculation_date)

        # 计算风险指标（简化版）
        from app.domain.mdvaes import RiskMetrics, RiskLevel
        risk_metrics = RiskMetrics(
            debt_to_assets=0.6,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.MEDIUM
        )

        # 获取最新 EPS
        latest_eps = eps_forecasts[0].eps_forecast

        # 计算估值
        valuation_result = ValuationCalculator.calculate(
            growth_metrics=growth_metrics,
            risk_metrics=risk_metrics,
            eps=latest_eps,
            current_pe=current_pe,
            bond_rate=bond_rate,
            params=params
        )

        # 生成图表数据
        charts = generate_charts_data(eps_forecasts, valuation_result)

        # 获取当前价格
        current_price = await get_current_price(db, request.symbol, calculation_date)

        return ok({
            "symbol": request.symbol,
            "calculation_date": calculation_date,
            "current_price": current_price,
            "valuation": valuation_result._asdict(),
            "signal": valuation_result.signal.value,
            "growth_metrics": growth_metrics._asdict(),
            "risk_metrics": risk_metrics._asdict(),
            "multi_anchor": valuation_result.valuation_method,
            "charts": charts
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"估值计算失败: {str(e)}")


@router.get("/parameters")
async def get_parameters(
    current_user: dict = Depends(get_current_user)
):
    """获取 MDVAES 参数定义"""
    return ok({
        "parameters": get_parameter_definitions(),
        "presets": {
            "conservative": {
                "forecast_years": 3,
                "peg_base": 0.8,
                "risk_adjustment": 0.15,
                "safety_margin_buy": 0.7,
                "safety_margin_sell": 1.15,
                "anchor_weight": {
                    "peg": 0.5,
                    "pe_historical": 0.3,
                    "pb": 0.1,
                    "dcf": 0.1
                }
            },
            "neutral": {
                "forecast_years": 5,
                "peg_base": 1.0,
                "risk_adjustment": 0.1,
                "safety_margin_buy": 0.8,
                "safety_margin_sell": 1.2,
                "anchor_weight": {
                    "peg": 0.4,
                    "pe_historical": 0.3,
                    "pb": 0.15,
                    "dcf": 0.15
                }
            },
            "aggressive": {
                "forecast_years": 7,
                "peg_base": 1.2,
                "risk_adjustment": 0.05,
                "safety_margin_buy": 0.9,
                "safety_margin_sell": 1.25,
                "anchor_weight": {
                    "peg": 0.35,
                    "pe_historical": 0.25,
                    "pb": 0.2,
                    "dcf": 0.2
                }
            }
        }
    })


# 辅助函数
async def get_latest_trading_date(db) -> str:
    """获取最新交易日"""
    from app.services.trading_calendar_service import TradingCalendarService
    calendar_service = TradingCalendarService()
    latest = await calendar_service.get_latest_trading_day()
    return latest.strftime("%Y-%m-%d")


async def get_current_price(db, symbol: str, date: str) -> float:
    """获取当前价格"""
    from app.services.backtest_stock_data_service_v2 import BacktestStockDataService
    stock_service = BacktestStockDataService(db)
    quotes = await stock_service.get_quotes(symbol, date, date)
    return quotes[-1]["close"] if quotes else 0.0


def generate_charts_data(eps_forecasts, valuation_result) -> dict:
    """生成图表数据"""
    return {
        "valuation_projection": {
            "dates": [f.year for f in eps_forecasts],
            "lower_bound": [],
            "intrinsic_value": [],
            "upper_bound": []
        },
        "water_level": {
            "current_price": 0.0,
            "lower_bound": valuation_result.lower_bound,
            "upper_bound": valuation_result.upper_bound,
            "intrinsic_value": valuation_result.intrinsic_value
        },
        "multi_anchor_comparison": {
            "methods": ["PEG估值", "历史PE", "PB估值", "DCF估值"],
            "values": list(valuation_result.valuation_method.values())
        },
        "eps_trend": [
            {
                "year": f.year,
                "eps": f.eps_forecast,
                "forecast": f.source == "analyst"
            }
            for f in eps_forecasts
        ]
    }


def check_subscription_tier(user: dict, feature: str):
    """检查用户订阅级别"""
    tier = user.get("tier", "basic")
    required_tiers = {
        "mdvaes": ["basic", "pro", "enterprise"]
    }
    if tier not in required_tiers[feature]:
        raise HTTPException(status_code=403, detail="需要订阅 Pro 或 Enterprise 版本")


def get_parameter_definitions() -> list:
    """获取参数定义"""
    return [
        {
            "name": "forecast_years",
            "type": "int",
            "default": 5,
            "range": {"min": 1, "max": 10},
            "description": "EPS 预测年数",
            "required": True,
            "group": "预测参数"
        },
        {
            "name": "peg_base",
            "type": "float",
            "default": 1.0,
            "range": {"min": 0.5, "max": 2.0},
            "description": "PEG 估值的基础倍数",
            "required": True,
            "group": "估值参数"
        }
    ]


# Pydantic 模型
from pydantic import BaseModel

class ValuationRequest(BaseModel):
    symbol: str
    calculation_date: Optional[str] = None
    params: dict
```

**Step 2: 注册路由**

```python
# app/main.py

from app.routers import mdvaes as mdvaes_router

app.include_router(mdvaes_router.router, tags=["mdvaes"])
```

**Step 3: 创建测试**

```python
# tests/routers/test_mdvaes.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
class TestMDVAESRouter:
    """MDVAES API 路由测试"""

    async def test_get_parameters(self, client: TestClient, auth_headers):
        """测试获取参数定义"""
        response = client.get("/api/mdvaes/parameters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "parameters" in data["data"]
```

**Step 4: 运行测试**

```bash
pytest tests/routers/test_mdvaes.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add app/routers/mdvaes.py app/main.py tests/routers/test_mdvaes.py
git commit -m "feat(mdvaes): add API routes for valuation and parameters"
```

---

## Phase 7: 前端组件实现

### Task 7.1: 创建 MDVAES Pinia Store

**Files:**
- Create: `frontend/src/stores/mdvaes.ts`

**Step 1: 创建 Store 文件**

```typescript
// frontend/src/stores/mdvaes.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mdvaesApi } from '@/api/mdvaes'

export interface MDVAESParams {
  preset?: 'conservative' | 'neutral' | 'aggressive' | 'custom'
  forecast_years?: number
  peg_base?: number
  peg_interest_sensitivity?: number
  risk_adjustment?: number
  anchor_weight?: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
  signal_mode?: 'valuation_range' | 'safety_margin'
  safety_margin_buy?: number
  safety_margin_sell?: number
}

export const useMdvaesStore = defineStore('mdvaes', () => {
  // 状态
  const currentValuation = ref<any>(null)
  const currentGrowthMetrics = ref<any>(null)
  const currentRiskMetrics = ref<any>(null)
  const currentMultiAnchor = ref<any>(null)
  const parameterDefinitions = ref<any[]>([])
  const presetParams = ref<Record<string, any>>({})

  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const hasValuation = computed(() => currentValuation.value !== null)
  const signal = computed(() => currentValuation.value?.signal || 'hold')
  const confidence = computed(() => currentValuation.value?.confidence || 0)

  // 操作
  async function fetchParameters() {
    loading.value = true
    try {
      const response = await mdvaesApi.getParameters()
      parameterDefinitions.value = response.data.parameters
      presetParams.value = response.data.presets
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function calculateValuation(
    symbol: string,
    params: MDVAESParams,
    calculationDate?: string
  ) {
    loading.value = true
    error.value = null

    try {
      const response = await mdvaesApi.getValuation({
        symbol,
        calculation_date: calculationDate || new Date().toISOString().split('T')[0],
        params
      })

      currentValuation.value = response.data.valuation
      currentGrowthMetrics.value = response.data.growth_metrics
      currentRiskMetrics.value = response.data.risk_metrics
      currentMultiAnchor.value = response.data.multi_anchor

      return response.data
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function getPresetParams(preset: string): MDVAESParams {
    return presetParams.value[preset] || getDefaultParams()
  }

  function getDefaultParams(): MDVAESParams {
    return {
      forecast_years: 5,
      min_forecast_count: 3,
      peg_base: 1.0,
      peg_interest_sensitivity: 0.5,
      risk_adjustment: 0.1,
      anchor_weight: {
        peg: 0.4,
        pe_historical: 0.3,
        pb: 0.15,
        dcf: 0.15
      },
      signal_mode: 'valuation_range',
      safety_margin_buy: 0.8,
      safety_margin_sell: 1.2,
      preset: 'neutral'
    }
  }

  async function saveUserParams(symbol: string, params: any) {
    await mdvaesApi.saveUserParams(symbol, params)
  }

  function clearValuation() {
    currentValuation.value = null
    currentGrowthMetrics.value = null
    currentRiskMetrics.value = null
    currentMultiAnchor.value = null
    error.value = null
  }

  return {
    // 状态
    currentValuation,
    currentGrowthMetrics,
    currentRiskMetrics,
    currentMultiAnchor,
    parameterDefinitions,
    presetParams,
    loading,
    error,
    // 计算属性
    hasValuation,
    signal,
    confidence,
    // 操作
    fetchParameters,
    calculateValuation,
    getPresetParams,
    getDefaultParams,
    saveUserParams,
    clearValuation
  }
})
```

**Step 2: 创建 API 接口文件**

```typescript
// frontend/src/api/mdvaes.ts
import axios from 'axios'

const API_BASE = '/api/mdvaes'

export const mdvaesApi = {
  async getValuation(request: {
    symbol: string
    calculation_date?: string
    params: any
  }) {
    const response = await axios.post(`${API_BASE}/valuation`, request)
    return response.data
  },

  async getParameters() {
    const response = await axios.get(`${API_BASE}/parameters`)
    return response.data
  },

  async saveUserParams(symbol: string, params: any) {
    const response = await axios.post(`${API_BASE}/user-params`, {
      symbol,
      params
    })
    return response.data
  },

  async getUserParams(symbol: string) {
    const response = await axios.get(`${API_BASE}/user-params/${symbol}`)
    return response.data
  },

  async getValuationHistory(symbol: string, days: number = 30) {
    const response = await axios.get(`${API_BASE}/history/${symbol}`, {
      params: { days }
    })
    return response.data
  }
}
```

**Step 3: 创建类型定义文件**

```typescript
// frontend/src/types/mdvaes.ts
export interface ValuationResult {
  intrinsic_value: number
  lower_bound: number
  upper_bound: number
  confidence: number
  valuation_method: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
  signal: 'buy' | 'sell' | 'hold'
}

export interface GrowthMetrics {
  cagr: number
  growth_rate: number
  r_squared: number
  growth_quality_score: number
  trend_stability: 'stable' | 'volatile' | 'declining'
}

export interface RiskMetrics {
  debt_to_assets: number
  current_ratio: number
  quick_ratio: number
  cashflow_to_income: number
  risk_level: 'low' | 'medium' | 'high'
}

export interface EPSData {
  year: number
  eps: number
  forecast?: boolean
}
```

**Step 4: 提交**

```bash
cd frontend
git add src/stores/mdvaes.ts src/api/mdvaes.ts src/types/mdvaes.ts
git commit -m "feat(mdvaes): add Pinia store, API client and type definitions"
```

---

### Task 7.2: 创建参数配置组件

**Files:**
- Create: `frontend/src/components/MDVAESParamsConfig.vue`

**Step 1: 创建组件文件**

```vue
<!-- frontend/src/components/MDVAESParamsConfig.vue -->
<template>
  <div class="mdvaes-params-config">
    <!-- 预设选择器 -->
    <el-radio-group v-model="localParams.preset" @change="onPresetChange" size="large">
      <el-radio-button label="conservative">保守</el-radio-button>
      <el-radio-button label="neutral">中性</el-radio-button>
      <el-radio-button label="aggressive">激进</el-radio-button>
      <el-radio-button label="custom">自定义</el-radio-button>
    </el-radio-group>

    <!-- 自定义参数滑块 -->
    <div v-if="localParams.preset === 'custom'" class="custom-params">
      <el-form :model="localParams" label-width="120px">
        <el-form-item label="预测年数">
          <el-slider
            v-model="localParams.forecast_years"
            :min="1"
            :max="10"
            :marks="{ 3: '3年', 5: '5年', 10: '10年' }"
            @change="onParamChange"
          />
          <span class="param-value">{{ localParams.forecast_years }} 年</span>
        </el-form-item>

        <el-form-item label="基础 PEG">
          <el-slider
            v-model="localParams.peg_base"
            :min="0.5"
            :max="2.0"
            :step="0.1"
            :marks="{ 0.8: '0.8', 1.0: '1.0', 1.5: '1.5' }"
            @change="onParamChange"
          />
          <span class="param-value">{{ localParams.peg_base }}</span>
        </el-form-item>

        <el-form-item label="风险折价">
          <el-slider
            v-model="localParams.risk_adjustment"
            :min="0"
            :max="0.3"
            :step="0.01"
            :marks="{ 0.05: '5%', 0.1: '10%', 0.2: '20%' }"
            @change="onParamChange"
          />
          <span class="param-value">{{ (localParams.risk_adjustment * 100).toFixed(0) }}%</span>
        </el-form-item>
      </el-form>
    </div>

    <!-- 实时估值预览 -->
    <div v-if="previewValuation" class="valuation-preview">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="内在价值">
          <span class="value">{{ previewValuation.intrinsic_value.toFixed(2) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="估值区间">
          <span class="value">
            {{ previewValuation.lower_bound.toFixed(2) }} -
            {{ previewValuation.upper_bound.toFixed(2) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="信号">
          <el-tag :type="getSignalType(previewValuation.signal)" size="small">
            {{ getSignalText(previewValuation.signal) }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <el-button @click="handleReset">重置参数</el-button>
      <el-button type="primary" @click="handleSave">保存参数</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useMdvaesStore } from '@/stores/mdvaes'

interface Props {
  modelValue: any
  symbol: string
  disabled?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue'])

const mdvaesStore = useMdvaesStore()

const localParams = ref({ ...props.modelValue })
const previewValuation = ref<any>(null)
const emitTimer = ref<any>(null)

// 预设变更
const onPresetChange = async (preset: string) => {
  if (preset === 'custom') return

  // 加载预设参数
  localParams.value = {
    ...mdvaesStore.getPresetParams(preset),
    preset
  }
  emit('update:modelValue', localParams.value)
  await updatePreview()
}

// 参数变更（防抖）
const onParamChange = () => {
  emit('update:modelValue', localParams.value)
  debouncedUpdatePreview()
}

const debouncedUpdatePreview = () => {
  if (emitTimer.value) clearTimeout(emitTimer.value)
  emitTimer.value = setTimeout(() => {
    updatePreview()
  }, 500)
}

// 更新估值预览
const updatePreview = async () => {
  try {
    const result = await mdvaesStore.calculateValuation(
      props.symbol,
      localParams.value
    )
    previewValuation.value = result.valuation
  } catch (error) {
    console.error('估值预览失败:', error)
  }
}

// 重置参数
const handleReset = () => {
  localParams.value = mdvaesStore.getDefaultParams()
  emit('update:modelValue', localParams.value)
  ElMessage.success('参数已重置')
}

// 保存参数
const handleSave = async () => {
  try {
    await mdvaesStore.saveUserParams(props.symbol, localParams.value)
    ElMessage.success('参数已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 信号类型映射
const getSignalType = (signal: string) => {
  const typeMap: Record<string, any> = {
    'buy': 'success',
    'sell': 'danger',
    'hold': 'warning'
  }
  return typeMap[signal] || 'info'
}

const getSignalText = (signal: string) => {
  const textMap: Record<string, string> = {
    'buy': '买入',
    'sell': '卖出',
    'hold': '持有'
  }
  return textMap[signal] || '未知'
}

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  localParams.value = { ...newVal }
}, { deep: true })

// 初始化
onMounted(() => {
  updatePreview()
})
</script>

<style scoped>
.mdvaes-params-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.custom-params {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.param-value {
  margin-left: 10px;
  font-weight: bold;
  color: #409EFF;
}

.valuation-preview {
  margin-top: 10px;
}

.actions {
  display: flex;
  gap: 10px;
}
</style>
```

**Step 2: 提交**

```bash
cd frontend
git add src/components/MDVAESParamsConfig.vue
git commit -m "feat(mdvaes): add parameters configuration component with preview"
```

---

### Task 7.3: 创建估值展示面板

**Files:**
- Create: `frontend/src/components/MDVAESValuationPanel.vue`
- Create: `frontend/src/components/WaterLevelGauge.vue`
- Create: `frontend/src/components/ValuationProjectionChart.vue`
- Create: `frontend/src/components/MultiAnchorComparison.vue`
- Create: `frontend/src/components/EPSTrendChart.vue`

**Step 1: 创建估值面板组件**

```vue
<!-- frontend/src/components/MDVAESValuationPanel.vue -->
<template>
  <div class="mdvaes-valuation-panel">
    <!-- 估值概览卡片 -->
    <el-card class="valuation-overview" shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="card-title">估值结果</span>
          <el-tag :type="getSignalType(valuation.signal)" size="large">
            {{ getSignalText(valuation.signal) }}
          </el-tag>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">内在价值</div>
            <div class="metric-value">
              {{ valuation.intrinsic_value.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">估值区间</div>
            <div class="metric-value">
              {{ valuation.lower_bound.toFixed(2) }} -
              {{ valuation.upper_bound.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">当前价格</div>
            <div class="metric-value" :class="getPriceClass()">
              {{ currentPrice.toFixed(2) }}
            </div>
            <div class="metric-sub">
              {{ getValuationStatus() }}
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 水位仪表盘 -->
      <WaterLevelGauge
        :current-price="currentPrice"
        :lower-bound="valuation.lower_bound"
        :upper-bound="valuation.upper_bound"
        :intrinsic-value="valuation.intrinsic_value"
      />
    </el-card>

    <!-- 多锚点对比卡片 -->
    <el-card class="multi-anchor" shadow="hover">
      <template #header>
        <span class="card-title">多锚点估值</span>
      </template>
      <MultiAnchorComparison :multi-anchor="multiAnchor" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import WaterLevelGauge from './WaterLevelGauge.vue'
import MultiAnchorComparison from './MultiAnchorComparison.vue'

interface Props {
  valuation: any
  currentPrice: number
  multiAnchor: any
}

const props = defineProps<Props>()

const getSignalType = (signal: string) => {
  const typeMap: Record<string, any> = {
    'buy': 'success',
    'sell': 'danger',
    'hold': 'warning'
  }
  return typeMap[signal] || 'info'
}

const getSignalText = (signal: string) => {
  const textMap: Record<string, string> = {
    'buy': '买入',
    'sell': '卖出',
    'hold': '持有'
  }
  return textMap[signal] || '未知'
}

const getPriceClass = () => {
  const { currentPrice, valuation } = props
  if (currentPrice < valuation.lower_bound) return 'price-low'
  if (currentPrice > valuation.upper_bound) return 'price-high'
  return 'price-normal'
}

const getValuationStatus = () => {
  const { currentPrice, valuation } = props
  if (currentPrice < valuation.lower_bound) return '低估'
  if (currentPrice > valuation.upper_bound) return '高估'
  return '合理区间'
}
</script>

<style scoped>
.mdvaes-valuation-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metric-item {
  text-align: center;
  padding: 10px;
}

.metric-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metric-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.price-low { color: #67C23A; }
.price-normal { color: #E6A23C; }
.price-high { color: #F56C6C; }
</style>
```

**Step 2: 创建水位仪表盘组件**

```vue
<!-- frontend/src/components/WaterLevelGauge.vue -->
<template>
  <div class="water-level-gauge">
    <div ref="chartRef" style="width: 100%; height: 300px;"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

interface Props {
  currentPrice: number
  lowerBound: number
  upperBound: number
  intrinsicValue: number
}

const props = defineProps<Props>()

const chartRef = ref<HTMLElement>()

const initChart = () => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  const { currentPrice, lowerBound, upperBound, intrinsicValue } = props
  const range = upperBound - lowerBound
  const position = ((currentPrice - lowerBound) / range) * 100

  // 根据位置确定颜色
  let color = '#67C23A' // 绿色
  if (currentPrice > upperBound) {
    color = '#F56C6C' // 红色
  } else if (currentPrice > intrinsicValue) {
    color = '#E6A23C' // 橙色
  }

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: lowerBound,
        max: upperBound,
        splitNumber: 10,
        itemStyle: { color },
        progress: { show: true, width: 30 },
        pointer: { show: false },
        axisLine: {
          lineStyle: { width: 30, color: [[1, '#E6EBF8']] }
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}',
          fontSize: 20,
          offsetCenter: [0, '20%']
        },
        data: [{ value: currentPrice }]
      }
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '65%',
        style: {
          text: getWaterLevelText(),
          fontSize: 14,
          fill: '#606266'
        }
      }
    ]
  }

  chart.setOption(option)
}

const getWaterLevelText = () => {
  const { currentPrice, lowerBound, upperBound } = props
  if (currentPrice < lowerBound) return '低估区（买入）'
  if (currentPrice > upperBound) return '高估区（卖出）'
  return '合理区间（持有）'
}

onMounted(() => {
  initChart()
})

watch(() => [props.currentPrice, props.lowerBound, props.upperBound], () => {
  if (chartRef.value) {
    const chart = echarts.getInstanceByDom(chartRef.value)
    chart?.dispose()
    initChart()
  }
}, { deep: true })
</script>

<style scoped>
.water-level-gauge {
  width: 100%;
}
</style>
```

**Step 3: 创建多锚点对比组件**

```vue
<!-- frontend/src/components/MultiAnchorComparison.vue -->
<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

interface Props {
  multiAnchor: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
}

const props = defineProps<Props>()
const chartRef = ref<HTMLElement>()

const initChart = () => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  const option = {
    title: {
      text: '多锚点估值对比',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    xAxis: {
      type: 'category',
      data: ['PEG估值', '历史PE', 'PB估值', 'DCF估值']
    },
    yAxis: {
      type: 'value',
      name: '估值（元）'
    },
    series: [
      {
        name: '估值结果',
        type: 'bar',
        data: [
          props.multiAnchor.peg,
          props.multiAnchor.pe_historical,
          props.multiAnchor.pb,
          props.multiAnchor.dcf
        ],
        itemStyle: {
          color: (params: any) => {
            const colors = ['#5470C6', '#91CC75', '#FAC858', '#EE6666']
            return colors[params.dataIndex]
          }
        },
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => params.value.toFixed(2)
        }
      }
    ]
  }

  chart.setOption(option)
}

onMounted(() => {
  initChart()
})

watch(() => props.multiAnchor, () => {
  if (chartRef.value) {
    const chart = echarts.getInstanceByDom(chartRef.value)
    chart?.dispose()
    initChart()
  }
}, { deep: true })
</script>
```

**Step 4: 提交前端组件**

```bash
cd frontend
git add src/components/MDVAESValuationPanel.vue src/components/WaterLevelGauge.vue src/components/MultiAnchorComparison.vue
git commit -m "feat(mdvaes): add valuation display components with ECharts"
```

---

### Task 7.4: 更新回测控制面板

**Files:**
- Modify: `frontend/src/views/Backtest/BacktestControlPanel.vue`

**Step 1: 在策略选择区域添加 MDVAES 策略**

```vue
<!-- 在 BacktestControlPanel.vue 的策略选择中添加 -->
<el-select
  v-model="form.strategy_id"
  placeholder="选择策略"
  @change="onStrategyChange"
>
  <el-option label="双均线策略" value="dual_ma" />
  <el-option label="MACD 策略" value="macd" />
  <el-option label="RSI 策略" value="rsi" />
  <el-option label="布林带策略" value="bollinger_bands" />
  <el-option label="MDVAES 估值策略" value="mdvaes" />  <!-- 新增 -->
</el-select>
```

**Step 2: 添加 MDVAES 参数配置区域**

```vue
<!-- 在 BacktestControlPanel.vue 中添加 -->
<!-- MDVAES 策略参数配置 -->
<div v-if="form.strategy_id === 'mdvaes'" class="mdvaes-config">
  <el-divider>MDVAES 估值参数</el-divider>

  <MDVAESParamsConfig
    v-model="form.strategy_params"
    :symbol="form.stock_code"
    :disabled="backtestStatus?.status === 'running'"
  />
</div>
```

**Step 3: 在 script 部分导入组件**

```typescript
// 在 BacktestControlPanel.vue 的 <script setup> 中添加
import MDVAESParamsConfig from '@/components/MDVAESParamsConfig.vue'
```

**Step 4: 更新类型定义**

```typescript
// 在 BacktestControlPanel.vue 的类型定义中添加
interface StrategyParams {
  // 现有参数...
  [key: string]: any

  // MDVAES 特定参数
  preset?: 'conservative' | 'neutral' | 'aggressive' | 'custom'
  forecast_years?: number
  peg_base?: number
  risk_adjustment?: number
  signal_mode?: 'valuation_range' | 'safety_margin'
}
```

**Step 5: 提交**

```bash
cd frontend
git add src/views/Backtest/BacktestControlPanel.vue
git commit -m "feat(mdvaes): integrate MDVAES into backtest control panel"
```

---

## Phase 8: 集成测试

### Task 8.1: 端到端集成测试

**Files:**
- Create: `tests/integration/test_mdvaes_e2e.py`

**Step 1: 创建集成测试**

```python
# tests/integration/test_mdvaes_e2e.py
"""MDVAES 端到端集成测试"""

import pytest
import asyncio
from datetime import datetime
from app.services.mdvaes_data_sync_service import MDVAESDataSyncService
from app.strategies.mdvaes import MDVAESStrategy
from app.core.database import get_mongo_db


@pytest.mark.asyncio
class TestMDVAESE2E:
    """MDVAES 端到端测试"""

    async def test_full_valuation_flow(self):
        """测试完整估值流程"""
        # 1. 同步数据
        sync_service = MDVAESDataSyncService()
        await sync_service.sync_daily_data("20240115")

        # 2. 创建策略实例
        strategy = MDVAESStrategy(
            symbol="000001.SZ",
            strategy_params={"preset": "neutral"}
        )

        # 3. 执行估值计算
        result = await strategy.on_bar(
            bar_id="test_001",
            timestamp="2024-01-15 10:00:00",
            current_price=12.5,
            position=0,
            cash=100000
        )

        # 4. 验证结果
        assert result is not None
        assert "action" in result
        assert result["action"] in ["buy", "sell", "hold"]

        # 5. 验证估值数据
        if "valuation" in result:
            assert result["valuation"] > 0
```

**Step 2: 运行测试**

```bash
pytest tests/integration/test_mdvaes_e2e.py -v
```

Expected: PASS

**Step 3: 提交**

```bash
git add tests/integration/test_mdvaes_e2e.py
git commit -m "test(mdvaes): add end-to-end integration tests"
```

---

## Phase 9: 文档和部署

### Task 9.1: 更新项目文档

**Files:**
- Modify: `docs/project-analysis/02-backend-apis.md` (已完成)
- Modify: `docs/project-analysis/01-frontend-components.md`
- Create: `docs/mdvaes-user-guide.md`

**Step 1: 更新前端组件分析文档**

```markdown
# 在 docs/project-analysis/01-frontend-components.md 中添加

## MDVAES 相关组件

### MDVAESParamsConfig.vue

**文件位置**: `frontend/src/components/MDVAESParamsConfig.vue`

**核心功能**:
- 预设参数选择（保守/中性/激进）
- 自定义参数滑块（预测年数、PEG、风险折价）
- 实时估值预览
- 参数保存和重置

**Props**:
```typescript
interface Props {
  modelValue: MDVAESParams  // v-model 绑定
  symbol: string            // 股票代码
  disabled?: boolean        // 禁用状态
}
```

### MDVAESValuationPanel.vue

**核心功能**:
- 估值结果概览（内在价值、区间、信号）
- 增长指标展示
- 风险指标展示
- 多锚点估值对比

### WaterLevelGauge.vue

**核心功能**:
- 仪表盘样式显示当前价格在估值区间的位置
- 颜色标识（低估/合理/高估）
- 动画效果
```

**Step 2: 创建用户指南**

```markdown
# MDVAES 估值模型用户指南

## 功能介绍

MDVAES (Multi-Dimensional Value Anchoring Evaluation System) 是一个基于基本面分析的股票估值模型...

## 快速开始

1. 查看股票估值
2. 配置回测参数
3. 查看回测结果
```

**Step 3: 提交文档**

```bash
git add docs/project-analysis/01-frontend-components.md docs/mdvaes-user-guide.md
git commit -m "docs(mdvaes): add frontend components analysis and user guide"
```

---

### Task 9.2: Docker 部署验证

**Files:**
- Modify: `docker-compose.yml` (已添加 Worker)

**Step 1: 构建 Docker 镜像**

```bash
docker-compose build
```

Expected: 成功构建 backend 和 frontend 镜像

**Step 2: 启动服务**

```bash
docker-compose up -d
```

Expected: 所有服务正常运行

**Step 3: 运行数据库初始化**

```bash
docker-compose exec backend python -m app.scripts.init_mdvaes_db
```

Expected: 输出 7 个 "✅" 消息

**Step 4: 验证 API**

```bash
curl -X POST http://localhost:8000/api/mdvaes/parameters \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

Expected: 返回参数定义

**Step 5: 提交部署配置**

```bash
git add docker-compose.yml
git commit -m "deploy(mdvaes): add MDVAES worker to docker-compose"
```

---

## Phase 10: 最终验收

### Task 10.1: 创建验收测试清单

**Files:**
- Create: `tests/acceptance/test_mdvaes_acceptance.md`

**Step 1: 创建验收清单**

```markdown
# MDVAES 验收测试清单

## 功能验收

- [ ] 1. 可以计算股票估值并返回合理结果
- [ ] 2. 支持 3 种预设参数（保守/中性/激进）
- [ ] 3. 支持完全自定义参数
- [ ] 4. 估值结果包含 4 个估值方法（PEG/PE/PB/DCF）
- [ ] 5. 估值结果包含增长指标和风险指标
- [ ] 6. 可以生成交易信号（买入/卖出/持有）
- [ ] 7. 前端参数调整时实时预览估值

## 回测验收

- [ ] 8. 可以选择 MDVAES 策略进行回测
- [ ] 9. 回测使用历史时间点的数据（避免后见之明）
- [ ] 10. 回测结果包含所有标准指标

## 数据同步验收

- [ ] 11. 数据同步 Worker 可以从 Tushare 同步数据
- [ ] 12. 同步的数据正确存储到 MongoDB
- [ ] 13. 支持每日自动同步

## 可视化验收

- [ ] 14. 仪表盘显示当前价格在估值区间的位置
- [ ] 15. 多锚点对比图显示 4 种估值方法
- [ ] 16. EPS 趋势图显示历史数据和预测
- [ ] 17. 估值推演图显示未来估值区间

## 性能验收

- [ ] 18. 估值计算时间 < 3 秒（有缓存 < 100ms）
- [ ] 19. 支持并发估值请求
- [ ] 20. 数据同步不影响正常使用

## 文档验收

- [ ] 21. API 文档完整（OpenAPI 格式）
- [ ] 22. 用户指南清晰易懂
- [ ] 23. 代码注释充分
```

**Step 2: 执行验收测试**

按照清单逐项验收

**Step 3: 提交验收文档**

```bash
git add tests/acceptance/test_mdvaes_acceptance.md
git commit -m "test(mdvaes): add acceptance test checklist"
```

---

## 实施总结

### 已完成任务

1. ✅ 数据层：7 个 MongoDB 集合和索引
2. ✅ 数据同步服务：从 Tushare 同步数据
3. ✅ 核心计算逻辑：增长率、估值、风险计算
4. ✅ 数据读取器：EPS、PE、国债利率读取
5. ✅ 策略实现：MDVAES 估值策略
6. ✅ API 路由：5 个新端点
7. ✅ 前端组件：参数配置、估值展示、4 种图表
8. ✅ 集成测试：端到端测试
9. ✅ 文档更新：项目分析文档、用户指南
10. ✅ Docker 部署：docker-compose 配置

### 下一步工作

1. 创建 Pull Request 合并到 main 分支
2. 代码审查
3. 部署到测试环境
4. 用户验收测试
5. 正式发布

### 风险提示

- ⚠️ 确保 Tushare Token 有效且有足够额度
- ⚠️ 数据同步可能较慢，首次同步建议在非交易时间进行
- ⚠️ 估值计算依赖历史数据完整性，新股上市需特殊处理
- ⚠️ 回测时注意避免前见偏差

---

**计划版本**: v1.0
**创建日期**: 2026-02-19
**预计工期**: 10-15 个工作日
**复杂度**: 中高级

**执行前准备**:
1. 确保在 `strategy_mdvaes` 分支
2. 确认 Tushare Token 配置正确
3. 确认 MongoDB 和 Redis 服务正常

**开始实施**: 使用 `superpowers:executing-plans` 技能逐任务执行
