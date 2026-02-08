"""
回测常用参数API路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from app.services.saved_params_service import get_saved_params_service, SavedParamsService
from app.models.backtest_params import (
    SavedBacktestParams,
    CreateSavedParamsRequest,
    UpdateSavedParamsRequest
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/backtest/saved-params",
    tags=["saved-params"]
)


@router.post("", response_model=SavedBacktestParams)
async def create_saved_params(
    request: CreateSavedParamsRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    创建保存的回测参数

    Args:
        request: 创建请求
        db: 数据库实例

    Returns:
        保存的参数
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        result = await service.create_params(user_id, request)
        return result
    except ValueError as e:
        logger.warning(f"⚠️ 创建常用参数失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 创建常用参数失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("", response_model=List[SavedBacktestParams])
async def get_saved_params_list(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    获取当前用户的所有保存参数

    Returns:
        参数列表
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        result = await service.get_user_params(user_id)
        return result
    except Exception as e:
        logger.error(f"❌ 获取常用参数列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/{params_id}", response_model=SavedBacktestParams)
async def get_saved_params(
    params_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    获取指定的保存参数

    Args:
        params_id: 参数ID

    Returns:
        参数对象
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        result = await service.get_params_by_id(params_id, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="参数不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取常用参数失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.put("/{params_id}", response_model=SavedBacktestParams)
async def update_saved_params(
    params_id: str,
    request: UpdateSavedParamsRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    更新保存的参数

    Args:
        params_id: 参数ID
        request: 更新请求

    Returns:
        更新后的参数
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        result = await service.update_params(params_id, user_id, request)
        if not result:
            raise HTTPException(status_code=404, detail="参数不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新常用参数失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{params_id}")
async def delete_saved_params(
    params_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    删除保存的参数

    Args:
        params_id: 参数ID

    Returns:
        删除结果
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        success = await service.delete_params(params_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="参数不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除常用参数失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{params_id}/use")
async def use_saved_params(
    params_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    使用保存的参数（增加使用次数）

    Args:
        params_id: 参数ID

    Returns:
        操作结果
    """
    # TODO: 从认证上下文获取用户ID
    user_id = "default"

    try:
        service = get_saved_params_service(db)
        success = await service.increment_usage(params_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="参数不存在")
        return {"success": True, "message": "使用次数已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新使用次数失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
