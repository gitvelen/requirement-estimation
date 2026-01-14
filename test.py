#!/usr/bin/env python
"""
evaluate接口测试脚本
"""
import requests

BASE_URL = "http://localhost:443/api/v1"


def test_evaluate():
    """测试evaluate接口"""
    url = f"{BASE_URL}/requirement/evaluate"
    file_path = "docs/附件三：需求变更申请表-支付中台系统配合新核心收付费流程改造需求 .docx"

    files = {"file": open(file_path, "rb")}
    data = {"request_id": "REQ-2024-TEST-001", "priority": "5"}

    response = requests.post(url, data=data, files=files)
    files["file"].close()

    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")

    return response.json()


def test_status(task_id):
    """查询任务状态"""
    url = f"{BASE_URL}/requirement/status/{task_id}"
    response = requests.get(url)
    print(f"状态: {response.json()}")
    return response.json()


if __name__ == "__main__":
    # 测试evaluate接口
    result = test_evaluate()

    # 查询任务状态
    if result.get("code") == 200:
        task_id = result["data"]["task_id"]
        print(f"\n任务ID: {task_id}")
        test_status(task_id)
