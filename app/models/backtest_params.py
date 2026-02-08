"""
回测常用参数数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SavedBacktestParams(BaseModel):
    """保存的回测参数"""
    id: Optional[str] = Field(None, description="参数ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")

    # 回测参数
    start_date: str = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    initial_capital: float = Field(..., gt=0, description="初始资金")
    min_purchase: int = Field(..., ge=100, le=10000, description="最小购买量")
    stock_code: str = Field(..., description="股票代码")

    # 策略相关
    strategy_id: str = Field(..., description="策略ID")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    usage_count: int = Field(default=0, description="使用次数")
    is_default: bool = Field(default=False, description="是否为默认参数")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "name": "常用配置-平安银行",
                "description": "平安银行2024年回测配置",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "initial_capital": 100000.0,
                "min_purchase": 100,
                "stock_code": "000001.SZ",
                "strategy_id": "dual_ma",
                "strategy_params": {
                    "short_period": 5,
                    "long_period": 20
                }
            }
        }


class CreateSavedParamsRequest(BaseModel):
    """创建保存参数请求"""
    name: str = Field(..., min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")
    params: Dict[str, Any] = Field(..., description="参数内容")


class UpdateSavedParamsRequest(BaseModel):
    """更新保存参数请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")
    params: Optional[Dict[str, Any]] = Field(None, description="参数内容")
