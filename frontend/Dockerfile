# 前端构建镜像（独立部署 - 多阶段构建）
# 构建阶段 + 运行阶段

# ============ 构建阶段 ============
FROM node:18-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖（使用国内镜像加速）
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/ && \
    npm ci

# 复制源码
COPY . .

# 构建前端
RUN npm run build

# ============ 运行阶段 ============
FROM nginx:alpine

# 删除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义 nginx 配置（指向远程后端）
COPY nginx-remote.conf /etc/nginx/nginx.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/build /usr/share/nginx/html

# 创建非root用户
RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /usr/share/nginx/html -s /sbin/nologin -G nginx-app -g nginx-app nginx-app

# 设置目录权限
RUN chown -R nginx-app:nginx-app /usr/share/nginx/html && \
    chown -R nginx-app:nginx-app /var/cache/nginx && \
    chown -R nginx-app:nginx-app /var/log/nginx && \
    chown -R nginx-app:nginx-app /etc/nginx/conf.d && \
    touch /run/nginx.pid && \
    chown -R nginx-app:nginx-app /run/nginx.pid

# 切换到非root用户
USER nginx-app

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
