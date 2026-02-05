"""
策略管理服务

提供策略的查询、参数校验等功能。
"""
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_mongo_db
from app.strategies.registry import StrategyRegistry
import logging

logger = logging.getLogger(__name__)


class StrategyService:
    """策略管理服务"""

    def __init__(self):
        self.db: AsyncIOMotorDatabase = get_mongo_db()
        self.strategies_collection = self.db.strategies
        self.categories_collection = self.db.strategy_categories

    async def get_strategy_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        根据策略ID获取策略

        Args:
            strategy_id: 策略ID

        Returns:
            策略文档，如果不存在返回None
        """
        return await self.strategies_collection.find_one({"strategy_id": strategy_id})

    async def strategy_exists(self, strategy_id: str) -> bool:
        """
        检查策略是否存在

        Args:
            strategy_id: 策略ID

        Returns:
            是否存在
        """
        count = await self.strategies_collection.count_documents({"strategy_id": strategy_id})
        return count > 0

    async def increment_usage_count(self, strategy_id: str):
        """
        增加策略使用次数

        Args:
            strategy_id: 策略ID
        """
        await self.strategies_collection.update_one(
            {"strategy_id": strategy_id},
            {"$inc": {"usage_count": 1}}
        )

    async def get_strategy_parameters(self, strategy_id: str) -> List[Dict[str, Any]]:
        """
        获取策略参数定义

        Args:
            strategy_id: 策略ID

        Returns:
            参数定义列表
        """
        strategy = await self.get_strategy_by_id(strategy_id)
        if not strategy:
            return []
        return strategy.get("parameters", [])

    async def search_strategies(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "usage_count",
        sort_order: int = -1,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        搜索策略

        Args:
            keyword: 搜索关键词
            category: 分类过滤
            sort_by: 排序字段
            sort_order: 排序顺序 (1升序, -1降序)
            skip: 跳过条数
            limit: 返回条数

        Returns:
            (策略列表, 总数)
        """
        query = {"is_builtin": True}  # 只返回内置策略

        if category:
            query["category"] = category

        if keyword:
            query["$text"] = {"$search": keyword}

        # 构建排序
        sort = [(sort_by, sort_order)]

        # 查询数据和总数
        cursor = self.strategies_collection.find(query).sort(sort).skip(skip).limit(limit)
        strategies = await cursor.to_list(length=limit)
        total = await self.strategies_collection.count_documents(query)

        return strategies, total

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有分类

        Returns:
            分类列表
        """
        cursor = self.categories_collection.find().sort("sort_order", 1)
        return await cursor.to_list(length=100)

    async def validate_parameters(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> tuple[bool, Optional[Dict[str, str]]]:
        """
        校验策略参数

        Args:
            strategy_id: 策略ID
            params: 参数字典

        Returns:
            (是否有效, 错误信息字典)
        """
        strategy = await self.get_strategy_by_id(strategy_id)
        if not strategy:
            return False, {"strategy": f"策略 {strategy_id} 不存在"}

        errors = {}

        for param_def in strategy["parameters"]:
            param_name = param_def["name"]
            param_type = param_def["type"]
            required = param_def.get("required", True)
            range_limit = param_def.get("range")
            options = param_def.get("options")

            # 必填检查
            if required and param_name not in params:
                errors[param_name] = f"参数 {param_name} 是必填的"
                continue

            if param_name not in params:
                continue

            param_value = params[param_name]

            # 类型检查
            if not self._validate_type(param_value, param_type):
                errors[param_name] = f"参数 {param_name} 类型错误，应为 {param_type}"
                continue

            # 范围检查
            if range_limit and not self._validate_range(param_value, range_limit):
                errors[param_name] = f"参数 {param_name} 超出范围 {range_limit}"
                continue

            # 选项检查
            if options and param_value not in options:
                errors[param_name] = f"参数 {param_name} 必须是以下之一: {options}"
                continue

        return len(errors) == 0, errors if errors else None

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """验证值类型"""
        type_map = {
            "int": int,
            "float": (int, float),
            "bool": bool,
            "string": str,
            "list": str
        }
        expected = type_map.get(expected_type)
        return isinstance(value, expected) if expected else False

    def _validate_range(self, value: Any, range_limit: Dict[str, Any]) -> bool:
        """验证值范围"""
        if not isinstance(value, (int, float)):
            return False

        if "min" in range_limit and value < range_limit["min"]:
            return False

        if "max" in range_limit and value > range_limit["max"]:
            return False

        return True

    async def get_categories_with_stats(self) -> List[Dict[str, Any]]:
        """
        获取分类及统计信息

        使用聚合管道一次性获取分类和策略数量

        Returns:
            分类列表（包含策略数量）
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "strategies",
                    "localField": "category_id",
                    "foreignField": "category",
                    "as": "strategies"
                }
            },
            {
                "$project": {
                    "category_id": 1,
                    "name": 1,
                    "description": 1,
                    "sort_order": 1,
                    "strategy_count": {"$size": "$strategies"}
                }
            },
            {
                "$sort": {"sort_order": 1}
            }
        ]

        cursor = self.categories_collection.aggregate(pipeline)
        return await cursor.to_list(length=100)


# 全局服务实例
_strategy_service: Optional[StrategyService] = None


def get_strategy_service() -> StrategyService:
    """获取策略管理服务实例"""
    global _strategy_service
    if _strategy_service is None:
        _strategy_service = StrategyService()
    return _strategy_service
