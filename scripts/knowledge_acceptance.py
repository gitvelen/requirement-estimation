#!/usr/bin/env python3
"""
知识库功能验收脚本

测试知识库的核心功能，包括：
1. Milvus连接测试
2. 知识库导入（CSV/DOCX）
3. 知识库检索
4. 统计信息
5. 效果评估指标

使用方法：
    python scripts/knowledge_acceptance.py

或者使用HTTP API：
    curl http://localhost:80/knowledge
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeAcceptanceTest:
    """知识库功能验收测试"""

    def __init__(self, base_url="http://localhost"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1/knowledge"
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def log_test(self, test_name, passed, message=""):
        """记录测试结果"""
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status} - {test_name}")
        if message:
            logger.info(f"    {message}")

        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_1_milvus_connection(self):
        """测试1：Milvus连接测试"""
        logger.info("\n" + "="*60)
        logger.info("测试1：Milvus连接测试")
        logger.info("="*60)

        try:
            # 检查Milvus容器是否运行
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=milvus", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            milvus_running = "milvus-standalone" in result.stdout

            if not milvus_running:
                self.log_test(
                    "Milvus容器状态",
                    False,
                    "Milvus容器未运行，请先启动: docker-compose --profile milvus up -d"
                )
                return False

            self.log_test("Milvus容器状态", True, "Milvus容器运行中")

            # 检查Milvus健康状态
            try:
                response = requests.get("http://localhost:9091/healthz", timeout=5)
                healthy = response.status_code == 200
                self.log_test(
                    "Milvus健康检查",
                    healthy,
                    f"HTTP {response.status_code}"
                )
            except Exception as e:
                self.log_test("Milvus健康检查", False, f"连接失败: {e}")
                return False

            # 检查知识库API
            try:
                response = requests.get(f"{self.api_base}/health", timeout=5)
                api_healthy = response.status_code == 200

                data = response.json()
                self.log_test(
                    "知识库API健康检查",
                    api_healthy,
                    f"状态: {data.get('status', 'unknown')}"
                )
            except Exception as e:
                self.log_test("知识库API健康检查", False, f"API调用失败: {e}")
                return False

            return True

        except Exception as e:
            self.log_test("Milvus连接测试", False, f"测试失败: {e}")
            return False

    def test_2_knowledge_stats(self):
        """测试2：获取知识库统计信息"""
        logger.info("\n" + "="*60)
        logger.info("测试2：知识库统计信息")
        logger.info("="*60)

        try:
            response = requests.get(f"{self.api_base}/stats", timeout=10)
            response.raise_for_status()

            data = response.json()
            stats = data.get("data", {})

            logger.info(f"知识库统计：")
            logger.info(f"  - Collection名称: {stats.get('name', 'N/A')}")
            logger.info(f"  - 知识总数: {stats.get('count', 0)} 条")
            logger.info(f"  - 索引类型: {stats.get('index', 'N/A')}")
            logger.info(f"  - 度量方式: {stats.get('metric_type', 'N/A')}")

            self.log_test(
                "获取统计信息",
                True,
                f"当前有 {stats.get('count', 0)} 条知识"
            )

            return True

        except Exception as e:
            self.log_test("获取统计信息", False, f"测试失败: {e}")
            return False

    def test_3_evaluation_metrics(self):
        """测试3：获取效果评估指标"""
        logger.info("\n" + "="*60)
        logger.info("测试3：效果评估指标")
        logger.info("="*60)

        try:
            response = requests.get(f"{self.api_base}/evaluation-metrics", timeout=10)
            response.raise_for_status()

            data = response.json()
            metrics = data.get("data", {})

            logger.info(f"效果评估指标：")
            logger.info(f"  - 检索命中率: {metrics.get('hit_rate', 0)}%")
            logger.info(f"  - 平均相似度: {metrics.get('avg_similarity', 0)}%")
            logger.info(f"  - 案例采纳率: {metrics.get('adoption_rate', 0)}%")
            logger.info(f"  - 总检索次数: {metrics.get('total_searches', 0)}")
            logger.info(f"  - 总评估任务: {metrics.get('total_tasks', 0)}")

            quality = metrics.get('quality_comparison')
            if quality:
                logger.info(f"  - 质量对比（使用知识库）: {quality.get('with_kb', 0)}%")
                logger.info(f"  - 质量对比（未使用知识库）: {quality.get('without_kb', 0)}%")

            self.log_test(
                "获取评估指标",
                True,
                "指标获取成功"
            )

            return True

        except Exception as e:
            self.log_test("获取评估指标", False, f"测试失败: {e}")
            return False

    def test_4_import_test_data(self):
        """测试4：导入测试数据"""
        logger.info("\n" + "="*60)
        logger.info("测试4：导入测试数据")
        logger.info("="*60)

        try:
            # 检查测试数据文件是否存在
            test_file = Path("data/templates/system_profile_template.csv")

            if not test_file.exists():
                self.log_test(
                    "导入测试数据",
                    False,
                    f"测试文件不存在: {test_file}"
                )
                return False

            # 读取文件并上传
            with open(test_file, 'rb') as f:
                files = {'file': ('test_system.csv', f, 'text/csv')}
                data = {'auto_extract': 'true'}

                response = requests.post(
                    f"{self.api_base}/import",
                    files=files,
                    data=data,
                    timeout=30
                )

                response.raise_for_status()
                result = response.json()

                success = result.get('data', {}).get('success', 0)
                failed = result.get('data', {}).get('failed', 0)

                logger.info(f"导入结果：成功 {success} 条，失败 {failed} 条")

                if success > 0:
                    self.log_test(
                        "导入测试数据",
                        True,
                        f"成功导入 {success} 条系统知识"
                    )
                    return True
                else:
                    self.log_test(
                        "导入测试数据",
                        False,
                        "没有数据导入成功"
                    )
                    return False

        except Exception as e:
            self.log_test("导入测试数据", False, f"测试失败: {e}")
            return False

    def test_5_knowledge_search(self):
        """测试5：知识检索测试"""
        logger.info("\n" + "="*60)
        logger.info("测试5：知识检索测试")
        logger.info("="*60)

        try:
            # 测试检索
            search_data = {
                "query": "支付中台 微信支付",
                "top_k": 5,
                "similarity_threshold": 0.6
            }

            response = requests.post(
                f"{self.api_base}/search",
                json=search_data,
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            total = result.get('data', {}).get('total', 0)
            results = result.get('data', {}).get('results', [])

            logger.info(f"检索结果：找到 {total} 条相关知识")

            if total > 0:
                logger.info(f"\n最相关的知识：")
                for i, item in enumerate(results[:3], 1):
                    logger.info(f"  {i}. {item.get('system_name', 'N/A')} - 相似度: {item.get('similarity', 0):.2f}")
                    logger.info(f"     {item.get('content', '')[:100]}...")

                self.log_test(
                    "知识检索",
                    True,
                    f"成功检索到 {total} 条相关知识"
                )
                return True
            else:
                self.log_test(
                    "知识检索",
                    False,
                    "未检索到相关知识（可能是知识库为空）"
                )
                return False

        except Exception as e:
            self.log_test("知识检索", False, f"测试失败: {e}")
            return False

    def test_6_save_case(self):
        """测试6：保存功能案例"""
        logger.info("\n" + "="*60)
        logger.info("测试6：保存功能案例")
        logger.info("="*60)

        try:
            # 测试保存案例
            case_data = {
                "system_name": "支付中台",
                "module": "测试模块",
                "feature_name": "验收测试功能",
                "description": "这是一个验收测试功能点",
                "estimated_days": 2.5,
                "complexity": "中",
                "tech_points": "Python、FastAPI",
                "dependencies": "核心系统",
                "project_case": "知识库验收测试",
                "source": "验收脚本"
            }

            response = requests.post(
                f"{self.api_base}/save_case",
                json=case_data,
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            if result.get('code') == 200:
                self.log_test(
                    "保存功能案例",
                    True,
                    "案例保存成功"
                )
                return True
            else:
                self.log_test(
                    "保存功能案例",
                    False,
                    f"保存失败: {result.get('message', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_test("保存功能案例", False, f"测试失败: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("\n" + "="*60)
        logger.info("知识库功能验收测试")
        logger.info("="*60)
        logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"API地址: {self.api_base}")
        logger.info("="*60)

        # 运行测试
        tests = [
            self.test_1_milvus_connection,
            self.test_2_knowledge_stats,
            self.test_3_evaluation_metrics,
            self.test_4_import_test_data,
            self.test_5_knowledge_search,
            self.test_6_save_case,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"测试执行异常: {e}")

        # 输出测试总结
        self.print_summary()

        # 生成验收报告
        self.generate_report()

    def print_summary(self):
        """打印测试总结"""
        logger.info("\n" + "="*60)
        logger.info("测试总结")
        logger.info("="*60)
        logger.info(f"总测试数: {len(self.test_results)}")
        logger.info(f"通过: {self.passed}")
        logger.info(f"失败: {self.failed}")
        logger.info(f"通过率: {self.passed / len(self.test_results) * 100:.1f}%")

        if self.failed == 0:
            logger.info("\n✓ 所有测试通过！知识库功能验收合格。")
        else:
            logger.info(f"\n✗ 有 {self.failed} 个测试失败，请检查日志。")

    def generate_report(self):
        """生成验收报告"""
        report = {
            "test_time": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": f"{self.passed / len(self.test_results) * 100:.1f}%",
            "results": self.test_results
        }

        # 保存到文件
        report_file = "data/knowledge_acceptance_report.json"
        os.makedirs("data", exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n验收报告已保存到: {report_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="知识库功能验收测试")
    parser.add_argument(
        "--base-url",
        default="http://localhost",
        help="API基础地址（默认: http://localhost）"
    )

    args = parser.parse_args()

    # 创建测试实例
    tester = KnowledgeAcceptanceTest(base_url=args.base_url)

    # 运行所有测试
    tester.run_all_tests()

    # 根据测试结果设置退出码
    sys.exit(0 if tester.failed == 0 else 1)


if __name__ == "__main__":
    main()
