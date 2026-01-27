"""
系统测试脚本
测试知识库导入和AI评估功能
"""
import requests
import time
import json

BASE_URL = "http://localhost:443/api/v1"

def test_health():
    """测试健康检查"""
    print("\n=== 测试1: 健康检查 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_knowledge_health():
    """测试知识库健康检查"""
    print("\n=== 测试2: 知识库健康检查 ===")
    try:
        response = requests.get(f"{BASE_URL}/knowledge/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_import_knowledge():
    """测试导入知识库"""
    print("\n=== 测试3: 导入系统知识 ===")
    try:
        with open("data/test_knowledge.csv", "rb") as f:
            files = {"file": ("test_knowledge.csv", f, "text/csv")}
            data = {"auto_extract": "true"}
            response = requests.post(f"{BASE_URL}/knowledge/import", files=files, data=data)
        
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_import_cases():
    """测试导入功能案例"""
    print("\n=== 测试4: 导入功能案例 ===")
    try:
        with open("data/test_cases.csv", "rb") as f:
            files = {"file": ("test_cases.csv", f, "text/csv")}
            data = {"auto_extract": "true"}
            response = requests.post(f"{BASE_URL}/knowledge/import", files=files, data=data)
        
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_knowledge_stats():
    """测试知识库统计"""
    print("\n=== 测试5: 知识库统计 ===")
    try:
        response = requests.get(f"{BASE_URL}/knowledge/stats")
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_search_knowledge():
    """测试知识检索"""
    print("\n=== 测试6: 知识检索 ===")
    try:
        payload = {
            "query": "账户管理功能",
            "top_k": 3,
            "similarity_threshold": 0.6
        }
        response = requests.post(f"{BASE_URL}/knowledge/search", json=payload)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_save_case():
    """测试保存功能案例"""
    print("\n=== 测试7: 保存功能案例 ===")
    try:
        payload = {
            "system_name": "新一代核心系统",
            "module": "账户管理",
            "feature_name": "测试功能点",
            "description": "这是一个测试功能点",
            "estimated_days": 2.5,
            "complexity": "低",
            "tech_points": "测试技术要点",
            "dependencies": "",
            "project_case": "自动化测试",
            "source": "测试脚本"
        }
        response = requests.post(f"{BASE_URL}/knowledge/save_case", json=payload)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("╔══════════════════════════════════════════╗")
    print("║   业务需求工作量评估系统 - 自动化测试    ║")
    print("╚══════════════════════════════════════════╝")
    
    tests = [
        ("健康检查", test_health),
        ("知识库健康检查", test_knowledge_health),
        ("导入系统知识", test_import_knowledge),
        ("导入功能案例", test_import_cases),
        ("知识库统计", test_knowledge_stats),
        ("知识检索", test_search_knowledge),
        ("保存功能案例", test_save_case),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
            time.sleep(1)  # 避免请求过快
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")
            results.append((name, False))
    
    # 打印测试结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)
    
    passed = 0
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
        if success:
            passed += 1
    
    print("="*50)
    print(f"总计: {passed}/{len(results)} 通过")
    print("="*50)

if __name__ == "__main__":
    main()
