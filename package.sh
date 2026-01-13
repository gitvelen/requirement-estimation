set -e

echo "========================================="
echo "需求评估系统 - 打包脚本"
echo "========================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 1. 构建前端
echo ""
echo "[步骤 1/3] 构建前端..."
cd frontend
npm install
npm run build
cd ..

echo "✓ 前端构建完成"

# 2. 构建Docker镜像
echo ""
echo "[步骤 2/3] 构建Docker镜像..."
docker-compose build

echo "✓ Docker镜像构建完成"

# 3. 打包项目
echo ""
echo "[步骤 3/3] 打包项目..."
cd ..

# 创建打包文件名
PACKAGE_NAME="requirement-system-$(date +%Y%m%d-%H%M%S).tar.gz"

# 打包（排除不必要的文件）
tar czf "$PACKAGE_NAME" \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='data/*' \
    --exclude='uploads/*' \
    --exclude='.DS_Store' \
    requirement-estimation-system/

echo "✓ 项目打包完成: $PACKAGE_NAME"

# 显示打包文件信息
echo ""
echo "========================================="
echo "打包完成！"
echo "========================================="
echo "打包文件: $PACKAGE_NAME"
ls -lh "$PACKAGE_NAME" | awk '{print "文件大小: " $5}'
echo ""
echo "下一步操作："
echo "1. 传输到目标服务器："
echo "   scp $PACKAGE_NAME root@目标服务器IP:/tmp/"
echo ""
echo "2. 在目标服务器解压并部署："
echo "   ssh root@目标服务器IP"
echo "   cd /tmp"
echo "   tar xzf $PACKAGE_NAME"
echo "   mv requirement-estimation-system /opt/"
echo "   cd /opt/requirement-estimation-system"
echo "   vim .env  # 配置API Key"
echo "   ./deploy.sh  # 执行部署脚本"
echo "========================================="
