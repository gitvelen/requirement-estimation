#!/bin/bash

# 依赖检查脚本
echo "🔍 检查 Python 依赖..."

# 方法1: 尝试导入所有模块
python3 -c "
import sys
sys.path.insert(0, '.')

# 尝试导入主应用
try:
    import backend.app
    print('✅ 主应用依赖检查通过')
except ImportError as e:
    print(f'❌ 依赖缺失: {e}')
    sys.exit(1)

# 检查关键模块
modules = [
    'fastapi',
    'uvicorn',
    'langchain',
    'langgraph',
    'dashscope',
    'pydantic'
]

missing = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError:
        missing.append(module)
        print(f'❌ {module}')

if missing:
    print(f'\n❌ 缺失依赖: {missing}')
    print('请运行: pip install -r requirements.txt')
    sys.exit(1)

print('\n✅ 所有依赖检查通过！')
"

# 方法2: 使用 pipreqs 对比
echo -e "\n📋 使用 pipreqs 检查是否有遗漏..."
pip install pipreqs -q
pipreqs . --force --savepath /tmp/tmp_requirements.txt 2>/dev/null

echo "当前 requirements.txt vs 实际代码使用:"
diff requirements.txt /tmp/tmp_requirements.txt || true
