#!/usr/bin/env python3
"""
测试回测历史记录API接口
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
import json
from datetime import datetime


# API 基础 URL
API_BASE = "http://localhost:8000"

# 测试用户token (需要根据实际情况修改)
# 这个token需要从登录接口获取,或者从浏览器的localStorage中复制
TEST_TOKEN = os.getenv("TEST_TOKEN", "")


async def test_get_history_list():
    """测试获取历史记录列表接口"""
    print("\n" + "="*80)
    print("测试 GET /api/backtest/history")
    print("="*80)

    if not TEST_TOKEN:
        print("❌ 错误: 未设置TEST_TOKEN环境变量")
        print("请先登录获取token,然后设置环境变量:")
        print("export TEST_TOKEN='your_jwt_token_here'")
        return None

    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }

    # 测试基本查询
    test_cases = [
        {
            "name": "基本查询（无参数）",
            "params": {}
        },
        {
            "name": "带分页参数",
            "params": {"skip": 0, "limit": 10}
        },
        {
            "name": "按股票代码筛选",
            "params": {"stock_code": "000001.SZ"}
        },
        {
            "name": "按策略筛选",
            "params": {"strategy_id": "dual_ma"}
        },
        {
            "name": "关键词搜索",
            "params": {"search": "双均线"}
        },
        {
            "name": "日期范围筛选",
            "params": {"start_date": "2023-01-01", "end_date": "2023-12-31"}
        },
        {
            "name": "初始资金范围筛选",
            "params": {"initial_capital_min": 100000, "initial_capital_max": 200000}
        },
        {
            "name": "收益率范围筛选",
            "params": {"return_rate_min": 0.05, "return_rate_max": 0.2}
        },
        {
            "name": "查看回收站",
            "params": {"include_deleted": True}
        }
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for test_case in test_cases:
            print(f"\n测试用例: {test_case['name']}")
            print(f"参数: {json.dumps(test_case['params'], ensure_ascii=False)}")

            try:
                response = await client.get(
                    f"{API_BASE}/api/backtest/history",
                    headers=headers,
                    params=test_case['params']
                )

                print(f"状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功")
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

                    # 检查返回的数据结构
                    if data.get("success"):
                        result = data.get("data", {})
                        records = result.get("records", [])
                        total = result.get("total", 0)

                        print(f"📊 返回记录数: {len(records)}")
                        print(f"📊 总记录数: {total}")

                        if records:
                            print(f"\n第一条记录示例:")
                            first_record = records[0]
                            print(f"  - record_id: {first_record.get('record_id')}")
                            print(f"  - name: {first_record.get('name')}")
                            print(f"  - stock_code: {first_record.get('parameters', {}).get('stock_code')}")
                            print(f"  - created_at: {first_record.get('created_at')}")
                    else:
                        print(f"❌ API返回success=False: {data.get('message', '未知错误')}")
                else:
                    print(f"❌ 请求失败")
                    print(f"响应内容: {response.text}")

            except Exception as e:
                print(f"❌ 异常: {e}")

    return response.status_code == 200


async def test_get_history_stats():
    """测试获取历史记录统计信息接口"""
    print("\n" + "="*80)
    print("测试 GET /api/backtest/history/stats")
    print("="*80)

    if not TEST_TOKEN:
        print("❌ 错误: 未设置TEST_TOKEN环境变量")
        return None

    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/api/backtest/history/stats",
                headers=headers
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功")
                print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

                if data.get("success"):
                    stats = data.get("data", {})
                    print(f"\n📊 统计信息:")
                    print(f"  - 当前记录数: {stats.get('current_count')}")
                    print(f"  - 上限: {stats.get('limit')}")
                    print(f"  - 剩余: {stats.get('remaining')}")
                    print(f"  - 使用率: {stats.get('usage_percent')}%")
                    print(f"  - 接近上限: {stats.get('near_limit')}")
                    print(f"  - 用户类型: {stats.get('user_type')}")
                else:
                    print(f"❌ API返回success=False: {data.get('message', '未知错误')}")
            else:
                print(f"❌ 请求失败")
                print(f"响应内容: {response.text}")

        except Exception as e:
            print(f"❌ 异常: {e}")


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("回测历史记录 API 测试")
    print("="*80)
    print(f"API基础URL: {API_BASE}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试获取历史记录列表
    await test_get_history_list()

    # 测试获取统计信息
    await test_get_history_stats()

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
