# vNext 部署与附件解析变更输入

## intent

用户要求在下一轮变更中完成以下事项：

1. 项目经理导入待评估工作量的需求文档时，当前已能解析 `docx`、`xlsx` 等附件，但不能解析 `txt` 格式附件，需要支持。
2. 发起评估页使用说明中的“上传需求文档（.docx / .doc / .xls 格式）”改为“上传需求文档（.docx格式）”。
3. 站点 HTTP 响应头需要新增 `Strict-Transport-Security: max-age=16070400`，验收命令以 `curl -I http://10.62.16.251:8000` 为准。
4. 修改 `docker-compose.backend.internal.yml`，删除 `- /etc/timezone:/etc/timezone:ro`。
5. `frontend/nginx.internal.conf` 中 `proxy_pass http://requirement-backend:443;` 的后端地址不应每次手工改成实际 IP，应放到 `.env.frontend` 中由部署脚本读取并渲染。
6. 前端服务部署时不应启动 443 端口服务。

## confirmed-decisions

- 上传格式口径：本轮只改页面展示文案，不收窄后端既有 `.doc/.xls` 兼容能力。
- HSTS 验收口径：`curl -I http://10.62.16.251:8000` 返回 `HTTP/1.1 200 OK` 且包含 `Strict-Transport-Security: max-age=16070400` 即可满足安全团队扫描。
- 前端 443 口径：前端部署不应暴露或启动 443，移除前端 compose、nginx 和部署脚本中的 443/SSL/HTTPS 证书启动路径。
- 头名口径：用户样例中的 `X-Content-Type-0ptions` 视为手误，实际实现继续使用标准头名 `X-Content-Type-Options`，避免破坏现有安全头语义。
- `.env.frontend` 口径：新增或明确 `FRONTEND_BACKEND_UPSTREAM`，用于配置前端 nginx 代理的实际后端地址；部署脚本可兼容旧的 `.env.frontend.internal` 作为回退。

## acceptance-examples

安全团队认可的 HTTP 入口头部形态如下，运行时动态头如 `Date`、`ETag`、`Content-Length` 不要求固定：

```text
HTTP/1.1 200 OK
Server: nginx/1.21.5
content-Type: text/html
X-XSS-Protection: 1; mode=block
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=16070400
```
