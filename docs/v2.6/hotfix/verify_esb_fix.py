#!/usr/bin/env python3
"""
ESB 修复验证脚本
用于验证 ESB_EMBEDDING_BATCH_SIZE 配置是否生效
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.config.config import settings

    print("=" * 60)
    print("ESB 修复配置验证")
    print("=" * 60)

    # 检查配置项是否存在
    if hasattr(settings, 'ESB_EMBEDDING_BATCH_SIZE'):
        batch_size = settings.ESB_EMBEDDING_BATCH_SIZE
        print(f"✓ ESB_EMBEDDING_BATCH_SIZE 配置已加载")
        print(f"  当前值: {batch_size}")

        # 验证值是否合理
        if batch_size <= 0:
            print(f"✗ 警告: 批次大小 {batch_size} 无效（应 > 0）")
            sys.exit(1)
        elif batch_size > 25:
            print(f"⚠ 注意: 批次大小 {batch_size} 较大，可能仍会遇到 400 错误")
        elif batch_size <= 5:
            print(f"⚠ 注意: 批次大小 {batch_size} 较小，导入速度可能较慢")
        else:
            print(f"✓ 批次大小设置合理（推荐范围: 5-15）")
    else:
        print("✗ 错误: ESB_EMBEDDING_BATCH_SIZE 配置项不存在")
        print("  请确认已应用补丁并重启服务")
        sys.exit(1)

    # 检查相关配置
    print("\n相关配置:")
    print(f"  EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
    print(f"  EMBEDDING_API_BASE: {settings.EMBEDDING_API_BASE or '(使用默认)'}")
    print(f"  KNOWLEDGE_ENABLED: {settings.KNOWLEDGE_ENABLED}")

    print("\n" + "=" * 60)
    print("验证通过！可以尝试重新导入 ESB 文档")
    print("=" * 60)

except ImportError as e:
    print(f"✗ 错误: 无法导入配置模块")
    print(f"  {e}")
    print("  请确认在项目根目录执行此脚本")
    sys.exit(1)
except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
