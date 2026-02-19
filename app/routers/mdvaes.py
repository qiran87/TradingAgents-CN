"""MDVAES 估值 API 路由"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.routers.auth_db import get_current_user
from app.models.mdvaes import (
    MDVAESCalculateRequest, MDVAESCalculateResponse,
    MDVAESParamsUpdateRequest, MDVAESParametersResponse,
    CacheStatusResponse, EPSForecastResponse
)
from app.services.mdvaes_service import get_mdvaes_service

router = APIRouter(prefix="/api/mdvaes", tags=["MDVAES估值"])
logger = logging.getLogger("webapi")


# ===== 估值计算端点 =====

@router.post("/calculate", summary="计算 MDVAES 估值", response_model=MDVAESCalculateResponse)
async def calculate_mdvaes_valuation(
    request: MDVAESCalculateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    计算多锚点估值

    基于分析师盈利预测或历史 EPS 外推，
    使用对数最小二乘法计算增长率，
    通过多锚点估值(PEG/PE/PB/DCF)计算内在价值。
    """
    service = get_mdvaes_service()

    result = await service.calculate_valuation(
        symbol=request.symbol,
        calculation_date=request.calculation_date,
        forecast_years=request.forecast_years,
        peg_base=request.peg_base,
        risk_adjustment=request.risk_adjustment,
        use_margin=request.use_margin,
        margin_buy=request.margin_buy,
        margin_sell=request.margin_sell
    )

    return result


# ===== 参数管理端点 =====

@router.get("/parameters", summary="获取 MDVAES 参数", response_model=MDVAESParametersResponse)
async def get_mdvaes_parameters(
    current_user: dict = Depends(get_current_user)
):
    """获取当前 MDVAES 参数配置"""
    service = get_mdvaes_service()
    return await service.get_default_parameters()


@router.put("/parameters", summary="更新 MDVAES 参数", response_model=MDVAESParametersResponse)
async def update_mdvaes_parameters(
    updates: MDVAESParamsUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    更新 MDVAES 参数

    只需要提供要更新的字段，未提供的字段保持不变。
    """
    service = get_mdvaes_service()

    # 过滤 None 值
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    return await service.update_parameters(update_dict)


# ===== EPS 预测端点 =====

@router.get("/forecasts/{symbol}", summary="获取 EPS 预测", response_model=list[EPSForecastResponse])
async def get_eps_forecasts(
    symbol: str,
    calculation_date: str,
    forecast_years: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定股票的 EPS 预测

    优先使用分析师预测，不足时使用历史数据外推。
    """
    service = get_mdvaes_service()

    try:
        forecasts = await service.get_eps_forecasts(
            symbol=symbol,
            calculation_date=calculation_date,
            forecast_years=forecast_years
        )
        return forecasts
    except Exception as e:
        logger.error(f"获取 EPS 预测失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 EPS 预测失败: {str(e)}"
        )


# ===== 缓存状态端点 =====

@router.get("/cache/status", summary="获取缓存状态", response_model=CacheStatusResponse)
async def get_cache_status(
    current_user: dict = Depends(get_current_user)
):
    """
    获取 MDVAES 缓存状态

    返回缓存条目数、缓存的股票列表等信息。
    """
    service = get_mdvaes_service()
    return await service.get_cache_status()
