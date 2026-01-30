# 使用官方Python镜像
FROM python:3.10-slim

# 使用阿里云 Debian 镜像加速（apt-get）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 定义构建参数（可通过 docker-compose 传递）
ARG UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
ENV UV_INDEX_URL=${UV_INDEX_URL}

# 安装系统依赖和 uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 复制项目配置文件（优先级高，利用缓存）
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# 使用 uv sync 安装依赖（从 lock 文件读取精确版本）
# --frozen: 确保不修改 lock 文件
# --no-dev: 不安装开发依赖
RUN uv sync --frozen --no-dev --index-url ${UV_INDEX_URL}

# 复制项目文件并设置权限
COPY --chown=appuser:appuser . .

# 创建必要的目录并设置权限
RUN mkdir -p logs data uploads && \
    chown -R appuser:appuser /app

# 将虚拟环境添加到 PATH（在验证之前设置）
ENV PATH="/app/.venv/bin:$PATH"

# 验证Python依赖是否完整（构建时检查）
RUN /app/.venv/bin/python -c "import sys; sys.path.insert(0, '.'); import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)

# 复制 entrypoint.sh 并设置权限
COPY --chown=appuser:appuser entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# 以 root 启动 entrypoint，便于修复挂载目录权限；entrypoint 内会降权运行主进程
USER root

# 暴露端口
EXPOSE 443

# 设置 entrypoint 和启动命令
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "443"]
