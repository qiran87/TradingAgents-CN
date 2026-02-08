"""
回测历史记录管理API路由
提供历史记录的保存、查询、对比、删除接口
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.core.database import get_mongo_db
from app.core.response import ok
from app.services.history_service import (
    HistoryService,
    HistoryRecordNotFoundError,
    BacktestResultNotFoundError,
    InvalidComparisonError,
    get_history_service
)
from app.routers.auth_db import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest-history"])


# ===================== 请求/响应模型 =====================

class SaveToHistoryRequest(BaseModel):
    """保存到历史记录请求"""
    name: str = Field(..., description="记录名称", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="记录描述", max_length=1000)
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")


class CompareHistoryRequest(BaseModel):
    """对比历史记录请求"""
    record_ids: List[str] = Field(..., description="历史记录ID列表（2-3个）", min_items=2, max_items=3)


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    record_ids: List[str] = Field(..., description="历史记录ID列表", min_items=1)
    permanent: bool = Field(False, description="是否永久删除")


# ===================== 依赖注入 =====================

def get_history_service_instance() -> HistoryService:
    """获取历史记录服务实例"""
    db = get_mongo_db()
    return get_history_service(db)


# ===================== API端点 =====================

@router.post("/{backtest_id}/save", response_model=dict)
async def save_to_history(
    backtest_id: str,
    request: SaveToHistoryRequest,
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    保存回测结果到历史记录

    将回测结果保存为历史记录，可以添加名称、描述和标签

    Args:
        backtest_id: 回测任务ID
        request: 保存请求（包含名称、描述、标签）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        保存的历史记录信息

    示例：
        - POST /api/backtest/bt_20240205_143055_123456/save
        - Body: {"name": "双均线策略-平安银行-2023年", "description": "测试双均线策略", "tags": ["双均线", "2023年"]}
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.save_to_history(
            backtest_id=backtest_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
            user_id=user_id
        )

        return ok(data=result)

    except BacktestResultNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 保存历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存历史记录失败: {str(e)}")


@router.get("/history", response_model=dict)
async def get_history_list(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    strategy_id: Optional[str] = Query(None, description="策略ID筛选"),
    stock_code: Optional[str] = Query(None, description="股票代码筛选"),
    search: Optional[str] = Query(None, description="关键词搜索"),
    include_deleted: bool = Query(False, description="是否包含已删除记录（回收站）"),
    start_date: Optional[str] = Query(None, description="回测开始日期筛选（YYYY-MM-DD格式）"),
    end_date: Optional[str] = Query(None, description="回测结束日期筛选（YYYY-MM-DD格式）"),
    initial_capital_min: Optional[float] = Query(None, description="最小初始资金筛选"),
    initial_capital_max: Optional[float] = Query(None, description="最大初始资金筛选"),
    return_rate_min: Optional[float] = Query(None, description="最小收益率筛选（0.1表示10%）"),
    return_rate_max: Optional[float] = Query(None, description="最大收益率筛选（0.1表示10%）"),
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    获取历史记录列表（增强版：支持日期范围、资金范围、收益率范围筛选）

    支持分页、多维度筛选和搜索功能

    Args:
        skip: 跳过记录数（分页用）
        limit: 返回记录数（默认20，最大100）
        strategy_id: 按策略ID筛选
        stock_code: 按股票代码筛选
        search: 按名称或描述搜索关键词
        include_deleted: 是否包含已删除记录（回收站）
        start_date: 回测开始日期筛选（YYYY-MM-DD格式）
        end_date: 回测结束日期筛选（YYYY-MM-DD格式）
        initial_capital_min: 最小初始资金筛选
        initial_capital_max: 最大初始资金筛选
        return_rate_min: 最小收益率筛选（0.1表示10%）
        return_rate_max: 最大收益率筛选（0.1表示10%）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        历史记录列表和总数

    示例：
        - GET /api/backtest/history?skip=0&limit=20
        - GET /api/backtest/history?strategy_id=dual_ma&stock_code=000001.SZ
        - GET /api/backtest/history?search=双均线
        - GET /api/backtest/history?start_date=2023-01-01&end_date=2023-12-31
        - GET /api/backtest/history?initial_capital_min=100000&initial_capital_max=200000
        - GET /api/backtest/history?return_rate_min=0.05&return_rate_max=0.2
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.get_history_list(
            user_id=user_id,
            skip=skip,
            limit=limit,
            strategy_id=strategy_id,
            stock_code=stock_code,
            search=search,
            include_deleted=include_deleted,
            start_date=start_date,
            end_date=end_date,
            initial_capital_min=initial_capital_min,
            initial_capital_max=initial_capital_max,
            return_rate_min=return_rate_min,
            return_rate_max=return_rate_max
        )

        return ok(data=result)

    except Exception as e:
        logger.error(f"❌ 获取历史记录列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史记录列表失败: {str(e)}")


@router.get("/history/stats", response_model=dict)
async def get_history_stats(
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    ✅ P2-4: 获取用户历史记录统计信息

    返回当前用户的历史记录使用情况，包括：
    - 当前记录数
    - 上限（普通用户100，管理员500）
    - 剩余可用空间
    - 使用百分比
    - 是否接近上限（超过80%）

    Args:
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        历史记录统计信息

    示例：
        - GET /api/backtest/history/stats
    """
    try:
        user_id = current_user.get("sub", "default")

        stats = await service.get_history_stats(user_id=user_id)

        return ok(data=stats)

    except Exception as e:
        logger.error(f"❌ 获取历史记录统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史记录统计失败: {str(e)}")


@router.get("/history/{record_id}", response_model=dict)
async def get_history_detail(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    获取历史记录详情

    获取历史记录的完整信息，包括回测结果

    Args:
        record_id: 历史记录ID
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        历史记录和完整回测结果

    示例：
        - GET /api/backtest/history/hist_20240205_001
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.get_history_detail(
            record_id=record_id,
            user_id=user_id
        )

        return ok(data=result)

    except HistoryRecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BacktestResultNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 获取历史记录详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史记录详情失败: {str(e)}")


@router.post("/history/compare", response_model=dict)
async def compare_history(
    request: CompareHistoryRequest,
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    对比历史记录

    对比2-3条历史记录的关键指标和资金曲线

    Args:
        request: 对比请求（包含记录ID列表）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        对比结果（包含各记录的指标和资金曲线）

    示例：
        - POST /api/backtest/history/compare
        - Body: {"record_ids": ["hist_20240205_001", "hist_20240205_002"]}
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.compare_history(
            record_ids=request.record_ids,
            user_id=user_id
        )

        return ok(data=result)

    except InvalidComparisonError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 对比历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"对比历史记录失败: {str(e)}")


@router.delete("/history/{record_id}", response_model=dict)
async def delete_history(
    record_id: str,
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    删除历史记录（支持软删除和永久删除）

    删除指定的历史记录，默认软删除（移至回收站）

    Args:
        record_id: 历史记录ID
        permanent: 是否永久删除（默认false，软删除）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        删除结果

    示例：
        - DELETE /api/backtest/history/hist_20240205_001 （软删除）
        - DELETE /api/backtest/history/hist_20240205_001?permanent=true （永久删除）
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.delete_history(
            record_id=record_id,
            user_id=user_id,
            permanent=permanent
        )

        return ok(data=result)

    except HistoryRecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 删除历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除历史记录失败: {str(e)}")


@router.post("/history/batch-delete", response_model=dict)
async def batch_delete_history(
    request: BatchDeleteRequest,
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    批量删除历史记录

    批量删除多条历史记录

    Args:
        request: 批量删除请求（包含record_ids和permanent标志）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        删除结果统计

    示例：
        - POST /api/backtest/history/batch-delete
        - Body: {"record_ids": ["hist_xxx", "hist_yyy"], "permanent": false}
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.batch_delete_history(
            record_ids=request.record_ids,
            user_id=user_id,
            permanent=request.permanent
        )

        return ok(data=result)

    except Exception as e:
        logger.error(f"❌ 批量删除失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.post("/history/{record_id}/restore", response_model=dict)
async def restore_history(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    恢复历史记录（从回收站）

    将软删除的历史记录恢复为正常状态

    Args:
        record_id: 历史记录ID
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        恢复结果

    示例：
        - POST /api/backtest/history/hist_20240205_001/restore
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.restore_history(
            record_id=record_id,
            user_id=user_id
        )

        return ok(data=result)

    except HistoryRecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 恢复历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复历史记录失败: {str(e)}")


@router.get("/history/{record_id}/export", response_model=dict)
async def export_history(
    record_id: str,
    format: str = Query("json", regex="^(json|excel|pdf)$", description="导出格式"),
    current_user: dict = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service_instance)
):
    """
    导出历史记录

    导出历史记录为指定格式（json/excel/pdf）

    Args:
        record_id: 历史记录ID
        format: 导出格式（json/excel/pdf）
        current_user: 当前用户
        service: 历史记录服务

    Returns:
        导出的数据

    示例：
        - GET /api/backtest/history/hist_20240205_001/export?format=json
        - GET /api/backtest/history/hist_20240205_001/export?format=excel
    """
    try:
        user_id = current_user.get("sub", "default")

        result = await service.export_history(
            record_id=record_id,
            format=format,
            user_id=user_id
        )

        return ok(data=result)

    except HistoryRecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 导出历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出历史记录失败: {str(e)}")
