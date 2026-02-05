"""
策略管理API路由

提供策略的查询、参数校验等接口。
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.services.strategy_service import get_strategy_service, StrategyService
from app.routers.auth_db import get_current_user

router = APIRouter(prefix="/api/backtest/strategies", tags=["backtest-strategies"])


# ===================== 请求/响应模型 =====================

class StrategyParameterRange(BaseModel):
    """参数范围"""
    min: Optional[float] = None
    max: Optional[float] = None


class StrategyParameter(BaseModel):
    """策略参数"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型: int/float/bool/string/list")
    default_value: Any = Field(..., description="默认值")
    range: Optional[StrategyParameterRange] = Field(None, description="取值范围")
    options: Optional[List[str]] = Field(None, description="可选值(list类型)")
    description: str = Field(..., description="参数说明")
    required: bool = Field(True, description="是否必填")


class StrategySummaryResponse(BaseModel):
    """策略摘要"""
    strategy_id: str
    name: str
    description: str
    category: str
    parameter_count: int
    usage_count: int
    is_builtin: bool


class StrategyDetailResponse(StrategySummaryResponse):
    """策略详情"""
    long_description: Optional[str] = None
    parameters: List[StrategyParameter]
    created_at: datetime


class StrategyCategoryResponse(BaseModel):
    """策略分类"""
    category_id: str
    name: str
    description: Optional[str] = None
    strategy_count: int = Field(0, description="该分类下的策略数量")


class ValidateParamsRequest(BaseModel):
    """参数校验请求"""
    params: dict = Field(..., description="参数键值对")


class ValidateParamsResponse(BaseModel):
    """参数校验响应"""
    valid: bool = Field(..., description="是否校验通过")
    errors: Optional[dict] = Field(None, description="错误信息")


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StrategySummaryResponse]
    total: int


# ===================== API端点 =====================

@router.get("/categories", response_model=List[StrategyCategoryResponse])
async def get_strategy_categories(
    current_user: dict = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """
    获取策略分类列表

    返回所有分类及每个分类下的策略数量
    """
    categories = await service.get_categories_with_stats()

    category_responses = []
    for category in categories:
        category_responses.append(StrategyCategoryResponse(
            category_id=category["category_id"],
            name=category["name"],
            description=category.get("description"),
            strategy_count=category.get("strategy_count", 0)
        ))

    return category_responses


@router.get("", response_model=StrategyListResponse)
async def get_strategies(
    category: Optional[str] = Query(None, description="按分类过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("usage_count", description="排序字段: usage_count/created_at/name"),
    sort_order: int = Query(-1, description="排序顺序: 1升序, -1降序"),
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(50, ge=1, le=100, description="返回条数"),
    current_user: dict = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """
    获取策略列表

    支持分类过滤、关键词搜索、排序、分页
    """
    # 使用service层查询策略
    strategies, total = await service.search_strategies(
        category=category,
        keyword=search,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )

    # 转换为响应模型
    strategy_summaries = []
    for strategy in strategies:
        strategy_summaries.append(StrategySummaryResponse(
            strategy_id=strategy["strategy_id"],
            name=strategy["name"],
            description=strategy["description"],
            category=strategy["category"],
            parameter_count=len(strategy["parameters"]),
            usage_count=strategy["usage_count"],
            is_builtin=strategy["is_builtin"]
        ))

    return StrategyListResponse(
        strategies=strategy_summaries,
        total=total
    )


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy_detail(
    strategy_id: str,
    current_user: dict = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """
    获取策略详情

    返回策略的完整信息，包括所有参数定义
    """
    strategy = await service.get_strategy_by_id(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")

    # 转换参数格式
    parameters = []
    for param in strategy["parameters"]:
        param_data = {
            "name": param["name"],
            "type": param["type"],
            "default_value": param["default_value"],
            "description": param["description"],
            "required": param.get("required", True)
        }
        if "range" in param:
            param_data["range"] = param["range"]
        if "options" in param:
            param_data["options"] = param["options"]
        parameters.append(StrategyParameter(**param_data))

    return StrategyDetailResponse(
        strategy_id=strategy["strategy_id"],
        name=strategy["name"],
        description=strategy["description"],
        long_description=strategy.get("long_description"),
        category=strategy["category"],
        parameters=parameters,
        usage_count=strategy["usage_count"],
        is_builtin=strategy["is_builtin"],
        parameter_count=len(strategy["parameters"]),
        created_at=strategy["created_at"]
    )


@router.post("/{strategy_id}/validate-params", response_model=ValidateParamsResponse)
async def validate_strategy_params(
    strategy_id: str,
    request: ValidateParamsRequest,
    current_user: dict = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """
    校验策略参数

    校验参数的类型、范围、必填等规则
    """
    is_valid, errors = await service.validate_parameters(
        strategy_id,
        request.params
    )

    return ValidateParamsResponse(
        valid=is_valid,
        errors=errors
    )
