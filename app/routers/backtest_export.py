"""
回测结果导出API路由
提供Excel、PDF等导出功能
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from app.services.export_service import get_export_service, ExportService
from tradingagents.utils.logging_init import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/backtest",
    tags=["backtest-export"]
)


@router.get("/{backtest_id}/export/excel")
async def export_backtest_excel(
    backtest_id: str,
    service: ExportService = Depends(get_export_service)
):
    """
    导出回测结果为Excel文件

    Args:
        backtest_id: 回测ID
        service: 导出服务实例（依赖注入）

    Returns:
        Excel文件下载响应

    Raises:
        HTTPException 404: 回测结果不存在
        HTTPException 500: 导出失败
    """
    logger.info(f"📥 收到Excel导出请求: {backtest_id}")

    try:
        # 调用导出服务
        excel_bytes, filename = await service.export_backtest_to_excel(
            backtest_id=backtest_id,
            user_id="default"  # TODO: 从认证上下文获取用户ID
        )

        # 返回文件下载响应
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-File-Name": filename,
                "X-Backtest-ID": backtest_id
            }
        )

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        if "BacktestResultNotFoundError" in error_type or "不存在" in error_msg:
            logger.warning(f"⚠️ 回测结果不存在: {backtest_id}")
            raise HTTPException(status_code=404, detail=f"回测结果不存在: {backtest_id}")
        else:
            logger.error(f"❌ 导出Excel失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"导出Excel失败: {error_msg}")


@router.get("/{backtest_id}/export/status")
async def get_export_status(
    backtest_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    检查回测结果是否可导出

    Args:
        backtest_id: 回测ID
        db: MongoDB数据库实例（依赖注入）

    Returns:
        导出状态信息
    """
    try:
        # 检查回测结果是否存在
        results = await db.backtest_results.find_one({
            "backtest_id": backtest_id
        })

        if not results:
            return {
                "success": False,
                "can_export": False,
                "message": "回测结果不存在",
                "backtest_id": backtest_id
            }

        # 检查交易明细是否存在
        trades_count = await db.backtest_trades.count_documents({
            "backtest_id": backtest_id
        })

        return {
            "success": True,
            "can_export": True,
            "message": "回测结果可导出",
            "backtest_id": backtest_id,
            "has_equity_curve": "equity_curve" in results,
            "trades_count": trades_count
        }

    except Exception as e:
        logger.error(f"❌ 检查导出状态失败: {e}", exc_info=True)
        return {
            "success": False,
            "can_export": False,
            "message": f"检查导出状态失败: {str(e)}",
            "backtest_id": backtest_id
        }
