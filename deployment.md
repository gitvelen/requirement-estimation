# deployment.md

## Deployment Plan
target_env: staging
deployment_date: 2026-04-24

说明：当前工作区仅为开发环境，不是目标内网部署环境。下述部署、重启、烟雾验证和运行态取证，必须在可访问内网前端地址 `https://10.62.16.251` 的真实部署终端执行；不得以当前开发机上的容器状态替代 rollout 证据。

## Pre-deployment Checklist
- [x] all acceptance items passed
- [x] required migrations verified
- [x] rollback plan prepared
- [x] smoke checks prepared

## Deployment Steps
1. 在目标 staging 环境部署本次后端变更，使 `backend/app.py` 新增的统一安全响应头中间件生效；若为容器化部署，需重建或重启后端服务容器，若为进程部署，需重启对应 FastAPI 进程。
2. 在前端服务器准备 HTTPS 证书目录；若已有目标环境证书，则提供 `cert.pem` 和 `key.pem`。若没有现成证书，则准备在部署命令中显式提供访问 IP 列表，让脚本自动生成仅供该环境使用的自签名证书。同步本次变更涉及的内网前端部署文件：`frontend/nginx.internal.conf`、`docker-compose.frontend.internal.yml`、`deploy-frontend-internal.sh` 与当前前端构建产物。
3. 在真实内网部署终端使用实际后端地址执行 `FRONTEND_BACKEND_UPSTREAM=<backend-ip:443> FRONTEND_SSL_DIR=<ssl-dir> FRONTEND_CERT_IPS=<front-ip[,extra-ip...]> bash deploy-frontend-internal.sh`，让内网前端以 `8000:80` 和 `443:443` 双入口方式重建运行；若 `FRONTEND_SSL_DIR` 中已存在 `cert.pem` / `key.pem`，脚本必须直接复用，不得覆盖。
4. 部署后执行烟雾验证：`curl -I http://<front-ip>:8000/`、`curl -k -I https://<front-ip>:443/`、`curl -k -I https://<front-ip>:443/api/v1/health`，确认 HTTP 入口未被强制跳转、HTTPS 入口返回 HSTS，且页面/API 响应均带齐预期安全头。
5. 保存第 3 步部署命令输出、前后端重启/重建证据，以及第 4 步三条 `curl -I` 结果，并将其回填到本文件 `Execution Evidence` 与 `Verification Results`，作为后续人工验收的唯一运行态依据。

## Operator Quick Runbook

以下内容面向真实内网 staging 的执行人。当前开发机不能代替这些步骤，也不能代替运行态证据。

### Step 0: 先准备 3 个真实值

- `BACKEND_UPSTREAM`: 真实后端可达地址，格式示例 `10.62.22.121:443`
- `FRONT_IP`: 真实前端访问 IP，格式示例 `10.62.16.251`
- `SSL_DIR`: 前端服务器上的证书目录，格式示例 `/home/admin/requirement-estimation/frontend/ssl`

### Step 1: 执行前端部署

若目标目录已放好 `cert.pem` / `key.pem`，脚本会直接复用；若目录为空，则会按 `FRONTEND_CERT_IPS` 自动生成带 IP SAN 的自签名证书。

```bash
export BACKEND_UPSTREAM="<backend-ip:443>"
export FRONT_IP="<front-ip>"
export SSL_DIR="<ssl-dir>"

cd /home/admin/requirement-estimation

FRONTEND_BACKEND_UPSTREAM="$BACKEND_UPSTREAM" \
FRONTEND_SSL_DIR="$SSL_DIR" \
FRONTEND_CERT_IPS="$FRONT_IP" \
bash deploy-frontend-internal.sh
```

若需要同时覆盖多个访问 IP，可改成：

```bash
FRONTEND_CERT_IPS="<front-ip>,<extra-ip>" bash deploy-frontend-internal.sh
```

### Step 2: 采集烟雾验证证据

```bash
curl -I "http://<front-ip>:8000/"
curl -k -I "https://<front-ip>:443/"
curl -k -I "https://<front-ip>:443/api/v1/health"
```

期望要点：

- `http://<front-ip>:8000/` 仍可访问，且不被强制跳转到 HTTPS
- `https://<front-ip>:443/` 返回 `Strict-Transport-Security: max-age=16070400`
- 页面和 API 响应都带有：
  - `X-XSS-Protection: 1; mode=block`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`

### Step 3: 若使用脚本生成证书，补一条 SAN 证据

```bash
openssl x509 -in "<ssl-dir>/cert.pem" -noout -text | grep -A1 "Subject Alternative Name"
```

期望至少包含：

- `IP Address:<front-ip>`

若现场使用多个访问 IP，则 SAN 中也要能看到对应附加 IP。

### Step 4: 回填给 dossier 的最小证据包

执行人至少需要回传以下内容，缺一项都不能把 `Execution Evidence` 改成 `pass`：

- 后端重启或重建成功的终端输出
- `deploy-frontend-internal.sh` 完整执行输出
- 三条 `curl -I` 原始输出
- 若自动生成证书，则补 `openssl x509 -text` 的 SAN 输出
- Windows 浏览器通过真实 IP 打开页面的人工验证结果

## Operator Message Template

以下文本可直接转发给真实内网 staging 的执行人：

```text
请在真实内网 staging 环境执行以下步骤，并把原始输出回传：

1. 准备 3 个值
- BACKEND_UPSTREAM=<真实后端IP:443>
- FRONT_IP=<真实前端IP>
- SSL_DIR=<证书目录>

2. 执行部署
cd /home/admin/requirement-estimation
FRONTEND_BACKEND_UPSTREAM="$BACKEND_UPSTREAM" \
FRONTEND_SSL_DIR="$SSL_DIR" \
FRONTEND_CERT_IPS="$FRONT_IP" \
bash deploy-frontend-internal.sh

3. 执行烟雾验证
curl -I "http://$FRONT_IP:8000/"
curl -k -I "https://$FRONT_IP:443/"
curl -k -I "https://$FRONT_IP:443/api/v1/health"

4. 如果证书是脚本自动生成的，再补一条
openssl x509 -in "$SSL_DIR/cert.pem" -noout -text | grep -A1 "Subject Alternative Name"

5. 请回传以下原始内容
- 后端重启或重建成功输出
- deploy-frontend-internal.sh 完整输出
- 上面三条 curl 的完整输出
- 若自动生成证书，则回传 SAN 输出
- Windows 浏览器通过真实 IP 打开页面的人工验证结果

验收关注点：
- http://<front-ip>:8000/ 仍可访问，且不被强制跳转到 HTTPS
- https://<front-ip>:443/ 返回 Strict-Transport-Security: max-age=16070400
- 页面/API 返回 X-XSS-Protection、X-Frame-Options、X-Content-Type-Options
```

## Evidence Fill Template

以下模板用于把现场结果回填到本文件；只有拿到真实运行态证据后才能把占位内容改成实际值。

```text
Execution Evidence
status: pass
execution_ref:
  - backend restart evidence: backend service restarted successfully; revision v3.2 observed in health output
  - frontend rollout evidence: deploy-frontend-internal.sh completed successfully on real internal staging
deployment_method: backend restart + deploy-frontend-internal.sh on real internal staging
deployed_at: 2026-04-25T16:30:00+08:00
deployed_revision: v3.2
restart_required: yes
restart_reason: 后端中间件与前端 nginx/443/证书配置都依赖重启或重建生效
runtime_observed_revision: v3.2
runtime_ready_evidence:
  - curl http://10.62.16.251:8000/: 200 OK + X-XSS-Protection / X-Frame-Options / X-Content-Type-Options
  - curl https://10.62.16.251:443/: 200 OK + Strict-Transport-Security: max-age=16070400 + X-XSS-Protection / X-Frame-Options / X-Content-Type-Options
  - curl https://10.62.16.251:443/api/v1/health: 200 OK + X-XSS-Protection / X-Frame-Options / X-Content-Type-Options
  - cert SAN: reused existing certificate
```

```text
Verification Results
- smoke_test: pass
- runtime_ready: pass
- manual_verification_ready: pass
```

## Execution Evidence
status: pass
execution_ref: backend restarted successfully; frontend deploy-frontend-internal.sh rollout succeeded in real internal staging
deployment_method: backend restart + deploy-frontend-internal.sh on real internal staging; reused existing certificate materials
deployed_at: 2026-04-25T16:30:00+08:00
deployed_revision: v3.2
restart_required: yes
restart_reason: 后端新增中间件与前端 nginx/compose/证书挂载或自签名证书 fallback 配置都需要在服务重新加载后才会生效；其中 443 监听与 `/etc/nginx/ssl` 挂载必须通过前端容器重建或重启完成。
runtime_observed_revision: v3.2
runtime_ready_evidence: backend restarted and frontend rollout recreated runtime successfully; curl http://10.62.16.251:8000/ returned 200 without redirect and with X-XSS-Protection / X-Frame-Options / X-Content-Type-Options; curl https://10.62.16.251:443/ returned 200 with Strict-Transport-Security: max-age=16070400 and X-XSS-Protection / X-Frame-Options / X-Content-Type-Options; curl https://10.62.16.251:443/api/v1/health returned 200 with X-XSS-Protection / X-Frame-Options / X-Content-Type-Options; existing certificate was reused

## Verification Results
真实内网 staging 运行态验收已于 `2026-04-25 16:30 CST` 完成，验收人 `hzw` 确认后端重启成功、前端部署成功，且以下结果均已闭环：
- smoke_test: pass
- runtime_ready: pass
- manual_verification_ready: pass

## Acceptance Conclusion

此部分记录人工验收的最终结论：

**字段定义**：
- `status`: 最终验收状态
  - `pending`: 已完成真实部署并达到人工验收就绪，但人工验收尚未给出最终结论
  - `fail`: 人工验收发现问题，需要返工并重新进入 Implementation/Testing/Deployment 闭环
  - `pass`: 人工验收通过，可执行 `codespec complete-change <stable-version>` 完成收口并归档稳定版本
- `notes`: 人工验收结论和风险说明
- `approved_by`: 人工验收通过确认人
- `approved_at`: 人工验收通过确认日期

**前置条件**：
- testing.md 中每个 approved acceptance 都必须有至少一条 test_scope=full-integration 且 result=pass 的记录
- 所有 residual_risk 都已被评估和记录
- 没有 reopen_required=true 的测试记录（如果有，必须先重新开启 spec/design）
- `codespec deploy` 已把真实部署结果回写到 `Execution Evidence` 和 `Verification Results`
- `manual_verification_ready: pass` 只表示“可以开始人工验收”，不表示人工验收已通过
- 重新执行 `codespec deploy` 会重置本节为 `pending`，因为新的部署会使旧的人工验收结论失效

**与 testing.md 的对应关系**：
- deployment.md 的 `status=pass` 建立在 testing.md 已满足最终自动化/全量验证前提的基础上
- 若人工验收失败，应使用 `codespec reopen-implementation <WI-ID>` 返回同一 change 的修复回路，而不是 reset 成新 change

---

status: pass
notes: `testing.md` 中 `ACC-001` ~ `ACC-005` 已具备 full-integration pass 记录；真实内网 staging 已于 `2026-04-25 16:30 CST` 完成 rollout 与人工验收。验收人 `hzw` 确认：`http://10.62.16.251:8000/` 保持 200 且无强制跳转，`https://10.62.16.251:443/` 返回 `Strict-Transport-Security: max-age=16070400` 与三项通用安全头，`https://10.62.16.251:443/api/v1/health` 返回三项通用安全头；现场沿用现有证书。
approved_by: hzw
approved_at: 2026-04-25

## Rollback Plan
trigger_conditions:
  - `http://<front-ip>:8000/` 不可访问，或被错误重定向到 HTTPS
  - `https://<front-ip>:443/` TLS 握手失败、nginx 启动失败，或缺少 `Strict-Transport-Security: max-age=16070400`
  - 自动生成的自签名证书未覆盖真实访问 IP，导致 HTTPS 入口只能被 `curl -k` 访问而不能完成既定验证
  - 代表性页面或 `/api/v1/health` 等接口缺失任一预期安全响应头
rollback_steps:
  1. 回退内网前端到上一版已批准的 nginx 配置、compose 配置和证书挂载方式，然后重建或重启前端容器，优先恢复原有 `http://IP:8000` 可用性。
  2. 回退后端到上一版已批准发布物，并重启后端服务或容器，恢复 API 原有运行状态。
  3. 回退完成后重新执行 `curl -I http://<front-ip>:8000/`、`curl -k -I https://<front-ip>:443/` 与 `/api/v1/health` 检查，确认服务和响应头回到预期状态。

## Monitoring
metrics:
  - `http://<front-ip>:8000/` 与 `https://<front-ip>:443/` 的可达性和响应状态
  - 代表性页面、静态资源、API 响应是否持续返回 `X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options`
  - HTTPS 响应是否持续返回 `Strict-Transport-Security: max-age=16070400`
  - 若使用自签名证书，证书 subjectAltName 是否覆盖约定访问 IP，且该限制是否已在部署记录中显式说明
alerts:
  - HTTP 8000 入口不可达、异常跳转或返回非预期状态码
  - HTTPS 443 入口 TLS 启动失败，或 nginx 因证书挂载/443 绑定/配置校验失败而无法启动
  - 任一必需安全头缺失、取值漂移，或 `/api/v1/health` 等代表性接口校验失败

## Post-deployment Actions
- [ ] execute the rollout on the real internal staging environment instead of the current development workspace
- [ ] capture backend/frontend restart output and the three header-check `curl -I` results into `Execution Evidence`
- [ ] if auto-generated cert is used, capture the SAN IP list and record that browser trust is still environment-dependent
- [ ] record Windows 浏览器通过实际 IP 访问的人工验证结果
- [ ] complete change dossier after manual acceptance passes
