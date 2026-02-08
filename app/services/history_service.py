"""
回测历史记录管理服务（增强版）
负责回测历史记录的保存、查询、对比、删除、批量操作和导出
"""
import logging
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from bson import ObjectId
import json
import io

logger = logging.getLogger(__name__)


# ===================== 异常类 =====================

class HistoryServiceError(Exception):
    """历史记录服务错误基类"""
    def __init__(self, message: str, code: str = "HISTORY_SERVICE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class HistoryRecordNotFoundError(HistoryServiceError):
    """历史记录不存在错误"""
    def __init__(self, record_id: str):
        self.record_id = record_id
        super().__init__(
            f"历史记录 {record_id} 不存在",
            "HISTORY_RECORD_NOT_FOUND"
        )


class BacktestResultNotFoundError(HistoryServiceError):
    """回测结果不存在错误"""
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id
        super().__init__(
            f"回测结果 {backtest_id} 不存在",
            "BACKTEST_RESULT_NOT_FOUND"
        )


class InvalidComparisonError(HistoryServiceError):
    """无效的对比请求错误"""
    def __init__(self, message: str):
        super().__init__(
            f"无效的对比请求: {message}",
            "INVALID_COMPARISON"
        )


# ===================== 历史记录管理服务 =====================

class HistoryService:
    """回测历史记录管理服务（增强版）"""

    # ✅ P2-4: 历史记录上限常量
    MAX_HISTORY_NORMAL = 100  # 普通用户最大记录数
    MAX_HISTORY_ADMIN = 500   # 管理员最大记录数

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化历史记录服务

        Args:
            db: MongoDB数据库实例
        """
        self.db = db

    async def _check_and_enforce_limit(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        ✅ P2-4: 检查并强制执行历史记录上限

        如果用户的历史记录数量达到上限，自动删除最旧的记录

        Args:
            user_id: 用户ID

        Returns:
            包含删除记录信息的字典
        """
        try:
            # 1. 获取用户信息（判断是否为管理员）
            user = await self.db.users.find_one({"username": user_id})
            is_admin = user.get("is_admin", False) if user else False

            # 2. 确定该用户的上限
            limit = self.MAX_HISTORY_ADMIN if is_admin else self.MAX_HISTORY_NORMAL

            # 3. 统计当前有效记录数（不包括已删除的）
            current_count = await self.db.backtest_history.count_documents({
                "user_id": user_id,
                "is_deleted": False
            })

            logger.info(f"📊 用户 {user_id} 当前记录数: {current_count}, 上限: {limit}")

            # 4. 如果达到上限，删除最旧的记录
            if current_count >= limit:
                # 查找最旧的记录
                oldest_record = await self.db.backtest_history.find_one({
                    "user_id": user_id,
                    "is_deleted": False
                }, sort=[("created_at", 1)])

                if oldest_record:
                    # 软删除该记录
                    await self.db.backtest_history.update_one(
                        {"_id": oldest_record["_id"]},
                        {
                            "$set": {
                                "is_deleted": True,
                                "deleted_at": datetime.now(timezone.utc),
                                "delete_reason": "auto_delete_limit_exceeded"
                            }
                        }
                    )

                    logger.info(f"🗑️  自动删除最旧记录: {oldest_record['record_id']} (用户: {user_id})")

                    return {
                        "deleted": True,
                        "deleted_record_id": oldest_record["record_id"],
                        "deleted_record_name": oldest_record["name"],
                        "current_count": current_count - 1,
                        "limit": limit,
                        "is_admin": is_admin
                    }

            return {
                "deleted": False,
                "current_count": current_count,
                "limit": limit,
                "is_admin": is_admin
            }

        except Exception as e:
            logger.error(f"❌ 检查历史记录上限失败: {e}", exc_info=True)
            # 检查失败时不阻止保存操作
            return {
                "deleted": False,
                "error": str(e)
            }

    async def save_to_history(
        self,
        backtest_id: str,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        保存回测结果到历史记录

        Args:
            backtest_id: 回测任务ID
            name: 记录名称
            description: 记录描述（可选）
            tags: 标签列表（可选）
            user_id: 用户ID（默认为"default"）

        Returns:
            保存的历史记录信息
        """
        try:
            logger.info(f"💾 保存回测结果到历史记录: {backtest_id}")

            # 1. 获取回测结果
            result = await self.db.backtest_results.find_one({"backtest_id": backtest_id})
            if not result:
                raise BacktestResultNotFoundError(backtest_id)

            # 2. 获取回测任务信息（获取参数）
            task = await self.db.backtest_tasks.find_one({"backtest_id": backtest_id})
            if not task:
                raise BacktestResultNotFoundError(backtest_id)

            # 3. 生成记录ID
            record_id = f"hist_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

            # 4. 提取关键指标快照
            metrics_snapshot = {
                "total_return": result.get("return_metrics", {}).get("total_return", 0.0),
                "max_drawdown": result.get("risk_metrics", {}).get("max_drawdown", 0.0),
                "sharpe_ratio": result.get("risk_adjusted_metrics", {}).get("sharpe_ratio", 0.0),
                "win_rate": result.get("trading_stats", {}).get("win_rate", 0.0),
                "total_trades": result.get("trading_stats", {}).get("total_trades", 0)
            }

            # 5. ✅ P2-4: 检查历史记录上限（自动删除最旧记录）
            limit_check = await self._check_and_enforce_limit(user_id)

            # 6. 构建历史记录文档（增加软删除支持）
            history_doc = {
                "record_id": record_id,
                "user_id": user_id,
                "name": name,
                "description": description or "",
                "tags": tags or [],
                "parameters": task.get("parameters", {}),
                "results_id": str(result["_id"]),
                "backtest_id": backtest_id,
                "metrics_snapshot": metrics_snapshot,
                "is_deleted": False,  # 软删除标志
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # 7. 插入数据库
            await self.db.backtest_history.insert_one(history_doc)

            logger.info(f"✅ 历史记录已保存: {record_id}")

            # ✅ P2-4: 返回上限检查信息
            response_data = {
                "record_id": record_id,
                "name": name,
                "message": "已保存到历史记录"
            }

            # 如果有自动删除,添加警告信息
            if limit_check.get("deleted"):
                response_data["warning"] = f"已达到上限({limit_check['limit']}条),自动删除最旧记录: {limit_check['deleted_record_name']}"
                response_data["deleted_record_id"] = limit_check["deleted_record_id"]
                response_data["current_count"] = limit_check["current_count"] + 1  # 加1是因为刚插入了新记录
                response_data["limit"] = limit_check["limit"]

            return response_data

        except BacktestResultNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 保存历史记录失败: {e}", exc_info=True)
            raise HistoryServiceError(f"保存历史记录失败: {str(e)}")

    async def get_history_stats(
        self,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        ✅ P2-4: 获取用户历史记录统计信息

        Args:
            user_id: 用户ID

        Returns:
            历史记录统计信息（当前数量、上限、是否接近上限等）
        """
        try:
            # 1. 获取用户信息（判断是否为管理员）
            user = await self.db.users.find_one({"username": user_id})
            is_admin = user.get("is_admin", False) if user else False

            # 2. 确定该用户的上限
            limit = self.MAX_HISTORY_ADMIN if is_admin else self.MAX_HISTORY_NORMAL

            # 3. 统计当前有效记录数（不包括已删除的）
            current_count = await self.db.backtest_history.count_documents({
                "user_id": user_id,
                "is_deleted": False
            })

            # 4. 计算使用百分比
            usage_percent = (current_count / limit) * 100 if limit > 0 else 0

            # 5. 判断是否接近上限（超过80%）
            near_limit = usage_percent >= 80

            # 6. 计算剩余可用空间
            remaining = max(0, limit - current_count)

            logger.info(f"📊 用户 {user_id} 历史记录统计: {current_count}/{limit} ({usage_percent:.1f}%)")

            return {
                "current_count": current_count,
                "limit": limit,
                "remaining": remaining,
                "usage_percent": round(usage_percent, 1),
                "near_limit": near_limit,
                "is_admin": is_admin,
                "user_type": "管理员" if is_admin else "普通用户"
            }

        except Exception as e:
            logger.error(f"❌ 获取历史记录统计失败: {e}", exc_info=True)
            raise HistoryServiceError(f"获取历史记录统计失败: {str(e)}")

    async def get_history_list(
        self,
        user_id: str = "default",
        skip: int = 0,
        limit: int = 20,
        strategy_id: Optional[str] = None,
        stock_code: Optional[str] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital_min: Optional[float] = None,
        initial_capital_max: Optional[float] = None,
        return_rate_min: Optional[float] = None,
        return_rate_max: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取历史记录列表（增强版：支持日期范围、资金范围、收益率范围筛选）

        Args:
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数
            strategy_id: 策略ID筛选（可选）
            stock_code: 股票代码筛选（可选）
            search: 关键词搜索（可选）
            include_deleted: 是否包含已删除记录（用于回收站）
            start_date: 回测开始日期筛选（可选，YYYY-MM-DD格式）
            end_date: 回测结束日期筛选（可选，YYYY-MM-DD格式）
            initial_capital_min: 最小初始资金筛选（可选）
            initial_capital_max: 最大初始资金筛选（可选）
            return_rate_min: 最小收益率筛选（可选，0.1表示10%）
            return_rate_max: 最大收益率筛选（可选，0.1表示10%）

        Returns:
            历史记录列表和总数
        """
        try:
            # 构建查询条件
            query = {"user_id": user_id}

            # 软删除过滤（除非明确要求包含已删除）
            if not include_deleted:
                query["is_deleted"] = False

            if strategy_id:
                query["parameters.strategy_id"] = strategy_id

            if stock_code:
                query["parameters.stock_code"] = stock_code

            if search:
                query["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]

            # ✅ 新增：时间区间筛选
            if start_date:
                query["parameters.start_date"] = {"$gte": start_date}
            if end_date:
                if "parameters.start_date" in query:
                    query["parameters.start_date"]["$lte"] = end_date
                else:
                    query["parameters.start_date"] = {"$lte": end_date}

            # ✅ 新增：初始资金范围筛选
            if initial_capital_min is not None:
                query["parameters.initial_capital"] = {"$gte": initial_capital_min}
            if initial_capital_max is not None:
                if "parameters.initial_capital" in query:
                    query["parameters.initial_capital"]["$lte"] = initial_capital_max
                else:
                    query["parameters.initial_capital"] = {"$lte": initial_capital_max}

            # ✅ 新增：收益率范围筛选
            if return_rate_min is not None:
                query["metrics_snapshot.total_return"] = {"$gte": return_rate_min}
            if return_rate_max is not None:
                if "metrics_snapshot.total_return" in query:
                    query["metrics_snapshot.total_return"]["$lte"] = return_rate_max
                else:
                    query["metrics_snapshot.total_return"] = {"$lte": return_rate_max}

            # 查询总数
            total = await self.db.backtest_history.count_documents(query)

            # ✅ 性能优化：使用投影减少返回数据量
            projection = {
                "_id": 0,
                "record_id": 1,
                "user_id": 1,
                "name": 1,
                "description": 1,
                "tags": 1,
                "parameters.stock_code": 1,
                "parameters.strategy_id": 1,
                "parameters.start_date": 1,
                "parameters.end_date": 1,
                "metrics_snapshot": 1,
                "is_deleted": 1,
                "created_at": 1,
                "updated_at": 1
                # 不返回results和完整parameters
            }

            # 查询记录（按创建时间倒序）
            cursor = self.db.backtest_history.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
            records = await cursor.to_list(length=limit)

            logger.info(f"📋 获取历史记录列表: 总数={total}, 返回={len(records)}")

            return {
                "records": records,
                "total": total
            }

        except Exception as e:
            logger.error(f"❌ 获取历史记录列表失败: {e}", exc_info=True)
            raise HistoryServiceError(f"获取历史记录列表失败: {str(e)}")

    async def get_history_detail(
        self,
        record_id: str,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        获取历史记录详情

        Args:
            record_id: 历史记录ID
            user_id: 用户ID

        Returns:
            历史记录和完整结果
        """
        try:
            # 查询历史记录
            history = await self.db.backtest_history.find_one({
                "record_id": record_id,
                "user_id": user_id
            })
            if not history:
                raise HistoryRecordNotFoundError(record_id)

            # 查询完整回测结果
            results_id = history.get("results_id")
            if isinstance(results_id, str):
                results_id = ObjectId(results_id)

            results = await self.db.backtest_results.find_one({"_id": results_id})
            if not results:
                raise BacktestResultNotFoundError(record_id)

            # 移除_id字段
            history.pop("_id", None)
            results.pop("_id", None)

            logger.info(f"📄 获取历史记录详情: {record_id}")

            return {
                "history": history,
                "results": results
            }

        except HistoryRecordNotFoundError:
            raise
        except BacktestResultNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 获取历史记录详情失败: {e}", exc_info=True)
            raise HistoryServiceError(f"获取历史记录详情失败: {str(e)}")

    async def compare_history(
        self,
        record_ids: List[str],
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        对比历史记录

        Args:
            record_ids: 历史记录ID列表（最多3条）
            user_id: 用户ID

        Returns:
            对比结果
        """
        try:
            if len(record_ids) > 3:
                raise InvalidComparisonError("最多只能对比3条记录")

            if len(record_ids) < 2:
                raise InvalidComparisonError("至少需要2条记录进行对比")

            records = []
            for record_id in record_ids:
                # 查询历史记录
                history = await self.db.backtest_history.find_one({
                    "record_id": record_id,
                    "user_id": user_id,
                    "is_deleted": False  # 不对比已删除的记录
                })
                if not history:
                    logger.warning(f"⚠️  历史记录不存在，跳过: {record_id}")
                    continue

                # 查询完整结果
                results_id = history.get("results_id")
                if isinstance(results_id, str):
                    results_id = ObjectId(results_id)

                results = await self.db.backtest_results.find_one({"_id": results_id})
                if not results:
                    logger.warning(f"⚠️  回测结果不存在，跳过: {record_id}")
                    continue

                # 组合数据
                records.append({
                    "record_id": record_id,
                    "name": history.get("name", ""),
                    "metrics_snapshot": history.get("metrics_snapshot", {}),
                    "parameters": history.get("parameters", {}),
                    "results": results
                })

            if len(records) < 2:
                raise InvalidComparisonError("有效记录不足2条，无法对比")

            logger.info(f"📊 对比历史记录: {len(records)}条")

            return {
                "records": records
            }

        except InvalidComparisonError:
            raise
        except Exception as e:
            logger.error(f"❌ 对比历史记录失败: {e}", exc_info=True)
            raise HistoryServiceError(f"对比历史记录失败: {str(e)}")

    async def delete_history(
        self,
        record_id: str,
        user_id: str = "default",
        permanent: bool = False
    ) -> Dict[str, Any]:
        """
        删除历史记录（支持软删除和永久删除）

        Args:
            record_id: 历史记录ID
            user_id: 用户ID
            permanent: 是否永久删除（默认False，使用软删除）

        Returns:
            删除结果
        """
        try:
            if permanent:
                # 永久删除
                result = await self.db.backtest_history.delete_one({
                    "record_id": record_id,
                    "user_id": user_id
                })

                if result.deleted_count == 0:
                    raise HistoryRecordNotFoundError(record_id)

                logger.info(f"🗑️  历史记录已永久删除: {record_id}")
                return {"message": "历史记录已永久删除"}
            else:
                # 软删除
                result = await self.db.backtest_history.update_one(
                    {"record_id": record_id, "user_id": user_id},
                    {
                        "$set": {
                            "is_deleted": True,
                            "deleted_at": datetime.now(timezone.utc)
                        }
                    }
                )

                if result.modified_count == 0:
                    raise HistoryRecordNotFoundError(record_id)

                logger.info(f"🗑️  历史记录已软删除: {record_id}")
                return {"message": "历史记录已移至回收站"}

        except HistoryRecordNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 删除历史记录失败: {e}", exc_info=True)
            raise HistoryServiceError(f"删除历史记录失败: {str(e)}")

    async def batch_delete_history(
        self,
        record_ids: List[str],
        user_id: str = "default",
        permanent: bool = False
    ) -> Dict[str, Any]:
        """
        批量删除历史记录

        Args:
            record_ids: 历史记录ID列表
            user_id: 用户ID
            permanent: 是否永久删除

        Returns:
            删除结果统计
        """
        try:
            if permanent:
                # 永久批量删除
                result = await self.db.backtest_history.delete_many({
                    "record_id": {"$in": record_ids},
                    "user_id": user_id
                })

                logger.info(f"🗑️  批量永久删除: {result.deleted_count}条记录")
                return {
                    "message": f"已永久删除{result.deleted_count}条记录",
                    "deleted_count": result.deleted_count
                }
            else:
                # 批量软删除
                result = await self.db.backtest_history.update_many(
                    {
                        "record_id": {"$in": record_ids},
                        "user_id": user_id
                    },
                    {
                        "$set": {
                            "is_deleted": True,
                            "deleted_at": datetime.now(timezone.utc)
                        }
                    }
                )

                logger.info(f"🗑️  批量软删除: {result.modified_count}条记录")
                return {
                    "message": f"已将{result.modified_count}条记录移至回收站",
                    "deleted_count": result.modified_count
                }

        except Exception as e:
            logger.error(f"❌ 批量删除失败: {e}", exc_info=True)
            raise HistoryServiceError(f"批量删除失败: {str(e)}")

    async def restore_history(
        self,
        record_id: str,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        从回收站恢复历史记录

        Args:
            record_id: 历史记录ID
            user_id: 用户ID

        Returns:
            恢复结果
        """
        try:
            result = await self.db.backtest_history.update_one(
                {"record_id": record_id, "user_id": user_id, "is_deleted": True},
                {
                    "$set": {"is_deleted": False},
                    "$unset": {"deleted_at": ""}
                }
            )

            if result.modified_count == 0:
                raise HistoryRecordNotFoundError(record_id)

            logger.info(f"♻️  历史记录已恢复: {record_id}")
            return {"message": "历史记录已恢复"}

        except HistoryRecordNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 恢复历史记录失败: {e}", exc_info=True)
            raise HistoryServiceError(f"恢复历史记录失败: {str(e)}")

    async def export_history(
        self,
        record_id: str,
        format: str = "json",
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        导出历史记录

        Args:
            record_id: 历史记录ID
            format: 导出格式（json/excel/pdf）
            user_id: 用户ID

        Returns:
            导出的数据
        """
        try:
            # 获取历史记录详情
            detail = await self.get_history_detail(record_id, user_id)

            if format == "json":
                # JSON格式导出
                export_data = {
                    "record": detail["history"],
                    "results": detail["results"],
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
                return {
                    "format": "json",
                    "data": export_data,
                    "filename": f"history_{record_id}.json"
                }

            elif format == "excel":
                # Excel格式导出（简化版，返回结构化数据）
                # 实际项目中可以使用openpyxl库生成Excel文件
                export_data = {
                    "基本信息": {
                        "记录名称": detail["history"]["name"],
                        "描述": detail["history"]["description"],
                        "标签": ", ".join(detail["history"]["tags"]),
                        "创建时间": detail["history"]["created_at"]
                    },
                    "回测参数": detail["history"]["parameters"],
                    "关键指标": {
                        "总收益率": f"{detail['history']['metrics_snapshot']['total_return']*100:.2f}%",
                        "最大回撤": f"{detail['history']['metrics_snapshot']['max_drawdown']*100:.2f}%",
                        "夏普比率": f"{detail['history']['metrics_snapshot']['sharpe_ratio']:.2f}",
                        "胜率": f"{detail['history']['metrics_snapshot']['win_rate']*100:.2f}%",
                        "交易次数": detail['history']['metrics_snapshot']['total_trades']
                    }
                }
                return {
                    "format": "excel",
                    "data": export_data,
                    "filename": f"history_{record_id}.xlsx"
                }

            elif format == "pdf":
                # PDF格式导出（简化版，返回结构化数据）
                # 实际项目中可以使用reportlab或weasyprint库生成PDF
                export_data = {
                    "title": detail["history"]["name"],
                    "description": detail["history"]["description"],
                    "metrics": detail["history"]["metrics_snapshot"],
                    "parameters": detail["history"]["parameters"],
                    "full_results": detail["results"]
                }
                return {
                    "format": "pdf",
                    "data": export_data,
                    "filename": f"history_{record_id}.pdf"
                }

            else:
                raise HistoryServiceError(f"不支持的导出格式: {format}")

        except HistoryRecordNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ 导出历史记录失败: {e}", exc_info=True)
            raise HistoryServiceError(f"导出历史记录失败: {str(e)}")


# ===================== 服务工厂函数 =====================

_history_service_instance: Optional[HistoryService] = None


def get_history_service(db: AsyncIOMotorDatabase) -> HistoryService:
    """
    获取历史记录服务实例

    Args:
        db: MongoDB数据库实例

    Returns:
        HistoryService实例
    """
    global _history_service_instance
    if _history_service_instance is None:
        _history_service_instance = HistoryService(db)
    return _history_service_instance
