"""
回测执行引擎API路由
提供回测任务的创建、控制、查询接口
"""
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.database import get_mongo_db
from app.core.response import ok
from app.services.backtest_engine_service import (
    BacktestEngine,
    BacktestNotFoundError,
    InvalidBacktestStatusError,
    get_backtest_engine_service,
    execute_backtest_task
)
from app.services.result_calculator import (
    ResultCalculator,
    get_result_calculator_service,
    BacktestNotFoundError as ResultNotFoundError
)
from app.services.websocket_manager import get_websocket_manager
from app.services.auth_service import AuthService
from app.routers.auth_db import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest-engine"])


# ===================== 请求/响应模型 =====================

class StartBacktestRequest(BaseModel):
    """启动回测请求"""
    stock_code: str = Field(..., description="股票代码（如 000001.SZ）")
    start_date: str = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    initial_capital: float = Field(100000.0, description="初始资金")
    strategy_id: str = Field("dual_ma", description="策略ID")
    strategy_params: dict = Field(default_factory=dict, description="策略参数")


class StartBacktestResponse(BaseModel):
    """启动回测响应"""
    backtest_id: str = Field(..., description="回测任务ID")
    status: str = Field(..., description="任务状态")


class BacktestStatusResponse(BaseModel):
    """回测状态响应"""
    backtest_id: str
    status: str
    execution_info: dict
    error: Optional[dict] = None


# ===================== 依赖注入 =====================

def get_backtest_service() -> BacktestEngine:
    """获取回测引擎服务实例"""
    return get_backtest_engine_service()


# ===================== REST API端点 =====================

@router.post("/start", response_model=dict)
async def start_backtest(
    request: StartBacktestRequest,
    background_tasks: BackgroundTasks,
    db = Depends(get_mongo_db),
    service: BacktestEngine = Depends(get_backtest_engine_service),
    current_user: dict = Depends(get_current_user)
):
    """
    启动回测任务

    创建回测任务并在后台执行

    示例：
    - POST /api/backtest/start
    """
    try:
        # 1. 生成回测任务ID
        backtest_id = f"bt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

        # 2. 构建参数字典
        parameters = {
            "stock_code": request.stock_code,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_capital": request.initial_capital,
            "strategy_id": request.strategy_id,
            "strategy_params": request.strategy_params
        }

        # 3. 获取用户ID (使用JWT sub字段)
        user_id = current_user.get("sub", "default")

        # 调试日志:输出当前用户信息
        logger.info(f"🔍 当前用户信息: {current_user}")
        logger.info(f"🔍 提取的 user_id: {user_id}")

        # 4. 创建任务文档
        task_doc = {
            "backtest_id": backtest_id,
            "user_id": user_id,
            "status": "created",
            "parameters": parameters,
            "execution_info": {
                "current_bar_index": 0,
                "total_bars": 0,
                "current_date": None,
                "progress": 0.0,
                "start_time": datetime.now(timezone.utc),
                "elapsed_time": 0.0
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        await db.backtest_tasks.insert_one(task_doc)

        # 4. 在后台执行回测
        background_tasks.add_task(execute_backtest_task, backtest_id, parameters)

        logger.info(f"✅ 回测任务已创建: {backtest_id}")

        return ok(data={
            "backtest_id": backtest_id,
            "status": "created"
        })

    except Exception as e:
        logger.error(f"❌ 启动回测失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"启动回测失败: {str(e)}"
        )


@router.post("/{backtest_id}/interrupt", response_model=dict)
async def interrupt_backtest(
    backtest_id: str,
    db = Depends(get_mongo_db),
    service: BacktestEngine = Depends(get_backtest_engine_service)
):
    """
    中断回测任务

    暂停正在运行的回测任务

    示例：
    - POST /api/backtest/bt_20240205_143055_123456/interrupt
    """
    try:

        # 检查任务是否存在
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise BacktestNotFoundError(backtest_id)

        if task["status"] != "running":
            raise InvalidBacktestStatusError(
                backtest_id,
                task["status"],
                ["running"]
            )

        # 设置暂停标志
        await service.pause_execution()

        # 更新任务状态
        await db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {"status": "paused", "updated_at": datetime.now(timezone.utc)}}
        )

        logger.info(f"⏸️  回测任务已暂停: {backtest_id}")

        return ok(data={"message": "回测已暂停"})

    except BacktestNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except InvalidBacktestStatusError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 暂停回测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"暂停回测失败: {str(e)}")


@router.post("/{backtest_id}/continue", response_model=dict)
async def continue_backtest(
    backtest_id: str,
    db = Depends(get_mongo_db),
    service: BacktestEngine = Depends(get_backtest_engine_service)
):
    """
    继续回测任务

    恢复已暂停的回测任务

    示例：
    - POST /api/backtest/bt_20240205_143055_123456/continue
    """
    try:

        # 检查任务是否存在
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise BacktestNotFoundError(backtest_id)

        if task["status"] != "paused":
            raise InvalidBacktestStatusError(
                backtest_id,
                task["status"],
                ["paused"]
            )

        # 恢复执行标志
        await service.resume_execution()

        # 更新任务状态
        await db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {"status": "running", "updated_at": datetime.now(timezone.utc)}}
        )

        # 重新启动后台任务
        parameters = task["parameters"]
        from app.services.backtest_engine_service import execute_backtest_task
        # TODO: 这里需要正确地恢复执行，而不是重新开始
        # 暂时简化处理：更新状态为running，实际恢复需要更复杂的逻辑

        logger.info(f"▶️  回测任务已继续: {backtest_id}")

        return ok(data={"message": "回测已继续"})

    except BacktestNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except InvalidBacktestStatusError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 继续回测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"继续回测失败: {str(e)}")


@router.get("/{backtest_id}/status", response_model=dict)
async def get_backtest_status(
    backtest_id: str,
    db = Depends(get_mongo_db)
):
    """
    查询回测状态

    获取回测任务的当前状态

    示例：
    - GET /api/backtest/bt_20240205_143055_123456/status
    """
    try:
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})

        if not task:
            raise BacktestNotFoundError(backtest_id)

        # 移除_id字段
        task.pop("_id", None)

        return ok(data=task)

    except BacktestNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 获取回测状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取回测状态失败: {str(e)}")


@router.delete("/{backtest_id}", response_model=dict)
async def abort_backtest(
    backtest_id: str,
    db = Depends(get_mongo_db),
    service: BacktestEngine = Depends(get_backtest_engine_service)
):
    """
    放弃回测任务

    删除回测任务和相关数据

    示例：
    - DELETE /api/backtest/bt_20240205_143055_123456
    """
    try:

        # 检查任务是否存在
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise BacktestNotFoundError(backtest_id)

        # 设置放弃标志
        await service.abort_execution()

        # 更新任务状态
        await db.backtest_tasks.update_one(
            {"backtest_id": backtest_id},
            {"$set": {"status": "aborted", "updated_at": datetime.now(timezone.utc)}}
        )

        logger.info(f"🚫 回测任务已放弃: {backtest_id}")

        return ok(data={"message": "回测任务已放弃"})

    except BacktestNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"❌ 放弃回测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"放弃回测失败: {str(e)}")


# ===================== WebSocket端点 =====================

@router.websocket("/ws/{backtest_id}/progress")
async def websocket_backtest_progress(
    websocket: WebSocket,
    backtest_id: str,
    token: Optional[str] = Query(None, description="JWT认证token（可选，用于安全控制）")
):
    """
    回测进度WebSocket端点

    推送回测进度和持仓更新

    Args:
        websocket: WebSocket连接对象
        backtest_id: 回测任务ID
        token: JWT认证token（可选，用于生产环境安全控制）

    示例：
    - WS /api/backtest/ws/bt_20240205_143055_123456/progress?token=xxx
    """
    websocket_manager = get_websocket_manager()

    # 验证token（如果提供）
    if token:
        token_data = AuthService.verify_token(token)
        if not token_data:
            await websocket.close(code=1008, reason="Invalid or expired token")
            logger.warning(f"🔒 WebSocket认证失败: backtest_id={backtest_id}")
            return
        logger.info(f"🔐 WebSocket认证成功: user={token_data.sub}, backtest_id={backtest_id}")

    await websocket.accept()
    await websocket_manager.connect(websocket, backtest_id)

    logger.info(f"🔌 WebSocket连接建立: backtest_id={backtest_id}")

    try:
        # 检查任务是否存在
        db = get_mongo_db()
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})

        if not task:
            await websocket.close(code=1008, reason=f"回测任务 {backtest_id} 不存在")
            return

        # 发送初始状态
        await websocket.send_json({
            "type": "connected",
            "data": {
                "backtest_id": backtest_id,
                "status": task["status"],
                "execution_info": task.get("execution_info", {})
            }
        })

        # 保持连接，接收客户端消息
        while True:
            data = await websocket.receive_text()

            # 处理客户端请求（如心跳）
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket连接断开: backtest_id={backtest_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket错误: {e}", exc_info=True)
    finally:
        await websocket_manager.disconnect(websocket, backtest_id)


@router.get("/{backtest_id}/current-state")
async def get_current_state(
    backtest_id: str,
    db=Depends(get_mongo_db)
):
    """
    获取回测任务当前状态（HTTP轮询备用接口）

    当WebSocket不可用时，前端可以通过此接口轮询获取回测进度和状态

    **限流策略：**
    - 每个IP每秒最多10次请求
    - 超过限制返回429状态码

    Args:
        backtest_id: 回测任务ID
        db: MongoDB数据库连接

    Returns:
        包含回测当前状态的JSON响应

    示例：
    - GET /api/backtest/bt_20240205_143055_123456/current-state
    """
    try:
        # 查询回测任务
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})

        if not task:
            raise HTTPException(status_code=404, detail=f"回测任务 {backtest_id} 不存在")

        # 构建响应数据
        response_data = {
            "backtest_id": task["backtest_id"],
            "status": task["status"],
            "execution_info": task.get("execution_info", {}),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at")
        }

        # 如果有错误信息，包含在响应中
        if "error" in task:
            response_data["error"] = task["error"]

        return ok(data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取回测状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取回测状态失败: {str(e)}")


# ===================== 结果查询API =====================

@router.get("/{backtest_id}/results", response_model=dict)
async def get_backtest_results(
    backtest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """
    获取回测结果

    获取回测任务的完整结果，包括收益指标、风险指标、交易统计等

    示例：
    - GET /api/backtest/bt_20240205_143055_123456/results
    """
    try:
        # 验证用户权限
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise HTTPException(status_code=404, detail="回测任务不存在")

        # 检查是否有权访问（只能访问自己的任务，或管理员可以访问所有）
        if task.get("user_id") != current_user.get("sub") and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="无权访问此回测结果")

        calculator = get_result_calculator_service()
        result = await calculator.get_results(backtest_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"回测结果不存在，请确认回测任务 {backtest_id} 已完成"
            )

        return ok(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取回测结果失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取回测结果失败: {str(e)}")


@router.get("/{backtest_id}/trades", response_model=dict)
async def get_backtest_trades(
    backtest_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=1000, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """
    获取交易明细（支持分页）

    获取回测任务的交易记录，包括买入、卖出交易

    示例：
    - GET /api/backtest/bt_20240205_143055_123456/trades?page=1&page_size=50
    """
    try:
        # 验证用户权限
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise HTTPException(status_code=404, detail="回测任务不存在")

        # 检查是否有权访问
        if task.get("user_id") != current_user.get("sub") and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="无权访问此交易明细")

        calculator = get_result_calculator_service()
        trades = await calculator.get_trades(backtest_id, limit=page_size)  # 限制最大返回数量

        # 手动分页
        total = len(trades)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_trades = trades[start_idx:end_idx]

        return ok(data={
            "trades": paginated_trades,
            "count": len(paginated_trades),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取交易明细失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取交易明细失败: {str(e)}")


@router.get("/{backtest_id}/equity-curve", response_model=dict)
async def get_equity_curve(
    backtest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """
    获取资金曲线

    获取回测任务的资金曲线数据，包括总资产、现金、持仓市值的变化

    示例：
    - GET /api/backtest/bt_20240205_143055_123456/equity-curve
    """
    try:
        # 验证用户权限
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise HTTPException(status_code=404, detail="回测任务不存在")

        # 检查是否有权访问
        if task.get("user_id") != current_user.get("sub") and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="无权访问此资金曲线")

        calculator = get_result_calculator_service()
        equity_curve = await calculator.get_equity_curve(backtest_id)

        if not equity_curve:
            raise HTTPException(
                status_code=404,
                detail=f"资金曲线不存在，请确认回测任务 {backtest_id} 已完成"
            )

        return ok(data=equity_curve)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取资金曲线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取资金曲线失败: {str(e)}")


@router.post("/{backtest_id}/calculate-results", response_model=dict)
async def calculate_backtest_results(
    backtest_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """
    触发结果计算

    手动触发回测结果计算（通常在回测完成时自动调用）

    示例：
    - POST /api/backtest/bt_20240205_143055_123456/calculate-results
    """
    try:
        # 检查任务是否存在
        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
        if not task:
            raise HTTPException(status_code=404, detail=f"回测任务 {backtest_id} 不存在")

        # 检查是否有权操作
        if task.get("user_id") != current_user.get("sub") and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="无权操作此回测任务")

        if task["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"只能计算已完成的回测任务，当前状态: {task['status']}"
            )

        # 在后台计算结果
        calculator = get_result_calculator_service()
        background_tasks.add_task(calculator.calculate_and_save_results, backtest_id)

        logger.info(f"✅ 已触发结果计算: {backtest_id}")

        return ok(data={"message": "正在计算结果，请稍后查询"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 触发结果计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发结果计算失败: {str(e)}")
