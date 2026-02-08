"""
回测常用参数服务
"""
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from app.models.backtest_params import SavedBacktestParams, CreateSavedParamsRequest, UpdateSavedParamsRequest
from tradingagents.utils.logging_init import get_logger

logger = get_logger(__name__)


class SavedParamsService:
    """常用参数服务"""

    MAX_PARAMS_PER_USER = 10

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.saved_backtest_params

    async def create_params(
        self,
        user_id: str,
        request: CreateSavedParamsRequest
    ) -> SavedBacktestParams:
        """
        创建保存的参数

        Args:
            user_id: 用户ID
            request: 创建请求

        Returns:
            保存的参数

        Raises:
            ValueError: 超过最大保存数量
        """
        # 检查是否超过最大数量
        count = await self.collection.count_documents({"user_id": user_id})
        if count >= self.MAX_PARAMS_PER_USER:
            raise ValueError(f"常用参数最多保存{self.MAX_PARAMS_PER_USER}组，请删除不常用参数后再保存")

        # 提取参数
        params = request.params
        saved_params = SavedBacktestParams(
            user_id=user_id,
            name=request.name,
            description=request.description,
            start_date=params.get("start_date", ""),
            end_date=params.get("end_date", ""),
            initial_capital=params.get("initial_capital", 100000),
            min_purchase=params.get("min_purchase", 100),
            stock_code=params.get("stock_code", ""),
            strategy_id=params.get("strategy_id", ""),
            strategy_params=params.get("strategy_params", {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 插入数据库
        result = await self.collection.insert_one(saved_params.model_dump(by_alias=True, exclude={"id"}))
        saved_params.id = str(result.inserted_id)

        logger.info(f"✅ 创建常用参数: {user_id} - {saved_params.name}")
        return saved_params

    async def get_user_params(self, user_id: str) -> List[SavedBacktestParams]:
        """
        获取用户的所有保存参数

        Args:
            user_id: 用户ID

        Returns:
            参数列表（按使用次数降序）
        """
        cursor = self.collection.find({"user_id": user_id}).sort("usage_count", -1)
        params_list = await cursor.to_list(length=None)

        return [
            SavedBacktestParams(
                id=str(param["_id"]),
                **{k: v for k, v in param.items() if k != "_id"}
            )
            for param in params_list
        ]

    async def get_params_by_id(self, params_id: str, user_id: str) -> Optional[SavedBacktestParams]:
        """
        根据ID获取参数

        Args:
            params_id: 参数ID
            user_id: 用户ID

        Returns:
            参数对象或None
        """
        param = await self.collection.find_one({"_id": params_id, "user_id": user_id})
        if not param:
            return None

        return SavedBacktestParams(
            id=str(param["_id"]),
            **{k: v for k, v in param.items() if k != "_id"}
        )

    async def update_params(
        self,
        params_id: str,
        user_id: str,
        request: UpdateSavedParamsRequest
    ) -> Optional[SavedBacktestParams]:
        """
        更新保存的参数

        Args:
            params_id: 参数ID
            user_id: 用户ID
            request: 更新请求

        Returns:
            更新后的参数或None
        """
        # 构建更新数据
        update_data = {"updated_at": datetime.now()}

        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.params is not None:
            params = request.params
            update_data["start_date"] = params.get("start_date")
            update_data["end_date"] = params.get("end_date")
            update_data["initial_capital"] = params.get("initial_capital")
            update_data["min_purchase"] = params.get("min_purchase")
            update_data["stock_code"] = params.get("stock_code")
            update_data["strategy_id"] = params.get("strategy_id")
            update_data["strategy_params"] = params.get("strategy_params", {})

        # 更新数据库
        result = await self.collection.update_one(
            {"_id": params_id, "user_id": user_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            return None

        # 返回更新后的数据
        return await self.get_params_by_id(params_id, user_id)

    async def delete_params(self, params_id: str, user_id: str) -> bool:
        """
        删除保存的参数

        Args:
            params_id: 参数ID
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        result = await self.collection.delete_one({"_id": params_id, "user_id": user_id})
        return result.deleted_count > 0

    async def increment_usage(self, params_id: str, user_id: str) -> bool:
        """
        增加使用次数

        Args:
            params_id: 参数ID
            user_id: 用户ID

        Returns:
            是否成功
        """
        result = await self.collection.update_one(
            {"_id": params_id, "user_id": user_id},
            {"$inc": {"usage_count": 1}}
        )
        return result.modified_count > 0


# ===================== 服务工厂函数 =====================

def get_saved_params_service(db) -> SavedParamsService:
    """
    获取常用参数服务实例

    Args:
        db: MongoDB数据库实例

    Returns:
        SavedParamsService实例
    """
    return SavedParamsService(db)
