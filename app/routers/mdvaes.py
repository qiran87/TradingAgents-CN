"""MDVAES 估值 API 路由"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from app.routers.auth_db import get_current_user
from app.models.mdvaes import (
    MDVAESCalculateRequest, MDVAESCalculateResponse,
    MDVAESParamsUpdateRequest, MDVAESParametersResponse,
    CacheStatusResponse, EPSForecastResponse
)
from app.services.mdvaes_service import get_mdvaes_service
from app.services.mdvaes_data_sync_service import get_mdvaes_sync_service
from app.core.database import get_mongo_db

router = APIRouter(prefix="/api/mdvaes", tags=["MDVAES估值"])
logger = logging.getLogger("webapi")


# ===== 批量同步数据模型 =====

class BatchSyncRequest(BaseModel):
    """批量同步请求"""
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", example="2015-01-01")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD", example="2016-12-31")


class BatchSyncResponse(BaseModel):
    """批量同步响应"""
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="提示信息")


class BatchSyncStatusResponse(BaseModel):
    """批量同步状态响应"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int
    message: Optional[str] = None
    result: Optional[dict] = None


# ===== 估值计算端点 =====


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


# ===== 批量历史数据同步端点 =====

@router.post("/batch-sync", summary="批量同步历史数据", response_model=BatchSyncResponse)
async def batch_sync_historical_data(
    request: BatchSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    批量同步历史 MDVAES 数据

    在后台异步执行，支持大范围时间段的同步（如 2015-2016 年）。
    优化 API 调用次数，一次性获取尽可能多的数据。

    **注意事项：**
    - 大范围同步可能需要较长时间
    - 建议非交易时间进行
    - 可通过 /batch-sync/{task_id}/status 查询进度
    """
    # 验证管理员权限
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可以执行批量同步"
        )

    # 生成任务ID
    import uuid
    task_id = f"mdvaes_batch_sync_{uuid.uuid4().hex[:8]}"

    # 在后台启动同步任务
    background_tasks.add_task(
        _run_batch_sync_task,
        task_id,
        request.start_date,
        request.end_date
    )

    return BatchSyncResponse(
        task_id=task_id,
        message=f"批量同步任务已启动，任务ID: {task_id}"
    )


@router.get("/batch-sync/{task_id}/status", summary="查询批量同步状态", response_model=BatchSyncStatusResponse)
async def get_batch_sync_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_mongo_db)
):
    """
    查询批量同步任务状态

    返回任务进度、当前消息和结果统计。
    """

    # 查询任务执行记录
    execution = await db.scheduler_executions.find_one(
        {"job_id": task_id},
        sort=[("timestamp", -1)]
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )

    return BatchSyncStatusResponse(
        task_id=task_id,
        status=execution.get("status", "unknown"),
        progress=execution.get("progress", 0),
        message=execution.get("progress_message"),
        result=execution.get("return_value") if execution.get("status") in ["success", "completed"] else None
    )


# ===== 后台任务函数 =====

async def _run_batch_sync_task(task_id: str, start_date: str, end_date: str):
    """后台执行批量同步任务"""
    import sys
    import os

    try:
        # 更新初始进度（直接插入执行记录）
        from app.core.database import get_mongo_db
        from datetime import datetime as dt
        db = get_mongo_db()

        execution_record = {
            "job_id": task_id,
            "job_name": f"MDVAES 批量同步 ({start_date} 至 {end_date})",
            "status": "running",
            "progress": 0,
            "progress_message": "正在初始化批量同步任务...",
            "scheduled_time": dt.now(),
            "timestamp": dt.now(),
            "is_manual": True
        }
        await db.scheduler_executions.insert_one(execution_record)

        # 执行批量同步
        service = get_mdvaes_sync_service()
        result = await service.batch_sync_historical_data(
            start_date=start_date,
            end_date=end_date,
            job_id=task_id
        )

        # 更新为完成状态
        await db.scheduler_executions.update_one(
            {"job_id": task_id, "status": "running"},
            {
                "$set": {
                    "status": "success",
                    "progress": 100,
                    "progress_message": "批量同步完成",
                    "return_value": result,
                    "updated_at": dt.now()
                }
            }
        )

        logger.info(f"✅ [批量同步] 任务 {task_id} 完成: {result}")

    except Exception as e:
        logger.error(f"❌ [批量同步] 任务 {task_id} 失败: {e}", exc_info=True)

        # 更新为失败状态
        try:
            from app.core.database import get_mongo_db
            from datetime import datetime as dt
            db = get_mongo_db()
            await db.scheduler_executions.update_one(
                {"job_id": task_id, "status": "running"},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "progress_message": f"批量同步失败: {str(e)}",
                        "updated_at": dt.now()
                    }
                }
            )
        except:
            pass
