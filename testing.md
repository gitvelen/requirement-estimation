# Testing Records

## How to Use This File

testing.md 是测试证据账本，记录本次变更各个 acceptance 的验证活动。
Implementation 阶段先记录 `branch-local` 结果，Testing 阶段再补齐 `full-integration` 结果。

**测试类型（test_type）**：
- `unit`: 单元测试
- `integration`: 集成测试
- `e2e`: 端到端测试
- `security`: 安全测试
- `manual`: 手工测试

**测试范围（test_scope）**：
- `branch-local`: Implementation 阶段的局部测试
- `full-integration`: Testing 阶段的完整集成测试

**测试结果（result）**：
- `pass`: 测试通过
- `fail`: 测试失败

**残留风险（residual_risk）**：
- `none`: 无残留风险
- `low`: 低风险
- `medium`: 中等风险
- `high`: 高风险

**重新开启标记（reopen_required）**：
- `true`: 需要重新开启 spec/design
- `false`: 不需要重新开启 spec/design

## Acceptance 到 Testing 的映射

本次变更的 acceptance 为 `ACC-001`、`ACC-002`、`ACC-003`、`ACC-004`、`ACC-005`。
每个 acceptance 在 Implementation 阶段至少需要补齐 branch-local 记录，在 Testing 阶段至少需要一条 `full-integration` 且 `result: pass` 的记录。

---

## Branch-Local Testing (Implementation Phase)

执行分支在 Implementation 阶段的测试记录。

### WI-001

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_backend_security_headers.py tests/test_frontend_nginx_upload_limit.py -q
  test_date: 2026-04-24
  artifact_ref: tests/test_backend_security_headers.py
  result: pass
  notes: 已验证后端 `/api/v1/health` 统一返回 `X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options`；三个 nginx 配置均为页面/静态资源补齐三项通用安全头，且 `/api/` 代理块未重复追加同名头。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q
  test_date: 2026-04-24
  artifact_ref: deploy-frontend-internal.sh
  result: pass
  notes: 已验证内网前端 compose 继续保留 `8000:80` 暴露，部署脚本未引入 `8000 -> 443` 自动跳转；临时 nginx 容器首页 `http://127.0.0.1:32769/` 可正常返回并携带三项通用安全头。Windows 浏览器通过实际 IP 的人工兼容性验证仍保留到 Testing/Deployment。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: security
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q
  test_date: 2026-04-24
  artifact_ref: frontend/nginx.internal.conf
  result: pass
  notes: 已验证内网前端配置包含 `listen 443 ssl`、证书路径 `/etc/nginx/ssl/cert.pem` 和 HSTS 头；临时 nginx 容器首页 `https://127.0.0.1:32768/` 返回 `Strict-Transport-Security: max-age=16070400` 及三项通用安全头，脚本/compose 测试同时覆盖 443 暴露、证书目录挂载和 HTTPS 健康检查。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: manual
  test_scope: branch-local
  verification_type: manual
  test_command: N/A
  test_date: 2026-04-24
  artifact_ref: design.md
  result: pass
  notes: 已复核 `design.md` 与 `work-items/WI-001.yaml`，确认 HSTS 复测入口为 `https://<前端IP>:443`，TLS 终止点为内网前端 nginx；证书优先由部署目录挂载，缺失时允许脚本按指定访问 IP 自动生成自签名证书；且本轮明确保留 `http://<前端IP>:8000` 兼容访问、不做自动重定向，也不把浏览器信任链闭环纳入范围。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_deploy_frontend_internal_script.py -q
  test_date: 2026-04-24
  artifact_ref: tests/test_deploy_frontend_internal_script.py
  result: pass
  notes: 已通过脚本级自动化测试验证：当 `cert.pem` / `key.pem` 缺失时，`deploy-frontend-internal.sh` 可在目标目录自动生成自签名证书；证书 `subjectAltName` 正确覆盖 `8.153.194.178` 和 `10.62.16.251`；若目录中已存在证书材料，脚本不会覆盖。另已用一次真实 bash 片段配合 `openssl x509 -text` 复核 SAN 输出。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: python -m pytest tests/test_backend_config_env_files.py -q
  test_date: 2026-04-24
  artifact_ref: tests/test_backend_config_env_files.py
  result: pass
  notes: 已验证 `Settings()` 在直接运行后端时可自动读取 `.env.backend` / `.env.backend.internal`；同时锁定 `.env.backend.example` 的必需参数集合，确保独立部署示例覆盖 `DASHSCOPE_API_BASE`、`EMBEDDING_API_BASE`、`EMBEDDING_MODEL`、鉴权参数与运行时基础参数，并采用贴近当前 IP 直连部署的示例值。
  residual_risk: low
  reopen_required: false

---

## Full Integration Testing (Testing Phase)

在 parent feature 分支的完整集成测试，作为最终验收依据。

- acceptance_ref: ACC-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_backend_security_headers.py tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q
  test_date: 2026-04-24
  artifact_ref: tests/test_backend_security_headers.py
  result: pass
  notes: fresh full-integration 已在 reopen Implementation 后重新执行完整 pytest 集合，结果为 `13 passed`；后端 `/api/v1/health` 的三项通用安全头，以及三个 nginx 配置的静态页/静态资源安全头基线均通过复核。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-002
  test_type: integration
  test_scope: full-integration
  verification_type: equivalent
  test_command: 临时 nginx 容器映射随机端口，使用运行时 nginx 配置执行 curl -I http://127.0.0.1:${HTTP_PORT}/
  test_date: 2026-04-24
  artifact_ref: frontend/nginx.internal.conf
  result: pass
  notes: fresh full-integration 等价验证使用运行时渲染配置与随机端口临时 nginx 容器复核；`http://127.0.0.1:32777/` 返回 `HTTP/1.1 200 OK`，未发生跳转，并携带三项通用安全头。这证明本轮在加入自签名证书 fallback 后，仍未把现有 HTTP/IP 访问强制切换到 HTTPS。Windows 浏览器实际 IP 验证可在 Deployment 再补人工证据。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-003
  test_type: security
  test_scope: full-integration
  verification_type: automated
  test_command: 临时 nginx 容器映射随机端口，使用运行时 nginx 配置执行 curl -k -I https://127.0.0.1:${HTTPS_PORT}/
  test_date: 2026-04-24
  artifact_ref: frontend/nginx.internal.conf
  result: pass
  notes: fresh full-integration 复核 `https://127.0.0.1:32776/` 返回 `HTTP/1.1 200 OK`，并携带 `Strict-Transport-Security: max-age=16070400` 及三项通用安全头；同一轮验证使用脚本自动生成的自签名证书启动临时 nginx 容器，满足 HSTS 复测入口要求。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-004
  test_type: manual
  test_scope: full-integration
  verification_type: manual
  test_command: N/A
  test_date: 2026-04-24
  artifact_ref: design.md
  result: pass
  notes: 已在 Testing 阶段复核 `spec.md`、`design.md`、`work-items/WI-001.yaml` 与 `testing.md`，确认 HSTS 复测入口、HTTPS/443 前提、“保留 http://IP:8000 兼容访问”的验证路径，以及“证书缺失时允许脚本生成自签名证书但不闭环浏览器信任链”的范围说明均已书面收口。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_deploy_frontend_internal_script.py -q；并以临时证书目录执行 ensure_https_certificate_materials + openssl x509 -text
  test_date: 2026-04-24
  artifact_ref: deploy-frontend-internal.sh
  result: pass
  notes: fresh full-integration 已重新执行脚本测试，验证缺证书时自动生成、已有证书时不覆盖；同时用真实 bash 片段在临时目录生成证书并经 `openssl x509 -text` 复核，证书 `subjectAltName` 明确包含 `8.153.194.178` 与 `10.62.16.251`。当前限制也已明确记录：该证书为自签名，仅用于 HTTPS/HSTS 闭环，不解决浏览器信任链。
  residual_risk: low
  reopen_required: false

- acceptance_ref: ACC-005
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  test_command: python -m pytest tests/test_backend_config_env_files.py tests/test_backend_security_headers.py tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_embedding_service_config.py -q
  test_date: 2026-04-24
  artifact_ref: tests/test_backend_config_env_files.py
  result: pass
  notes: 在 Testing 阶段重新执行与本次 reopen 直接相关的完整回归，结果为 `20 passed`。其中新增验证确认：`Settings()` 会自动读取 `.env.backend` / `.env.backend.internal`，`.env.backend.example` 已补齐独立部署所需的运行参数、LLM/Embedding 参数、鉴权参数与任务/上传参数，且示例值保持贴近当前 IP 直连部署口径；同时安全头与前端部署脚本既有测试继续通过，证明本次配置收口未破坏原整改链路。
  residual_risk: low
  reopen_required: false

---

## Summary

- 当前状态：本轮 reopen Implementation 后，`ACC-001` ~ `ACC-005` 的 branch-local 与 fresh full-integration 记录均已补齐并通过；其中 `ACC-005` 已补充后端 env file 读取与 `.env.backend.example` 完整性的 fresh full-integration 证据。

## Local Reproduction (Development Workspace)

以下命令用于在当前开发机复测安全团队扫描出的 4 项问题是否已按本轮设计闭环；它们不是 staging rollout 证据，也不能替代 `deployment.md` 要求的真实内网运行态取证。

### Backend API: 3 个通用安全头

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from backend.app import app

with TestClient(app) as client:
    response = client.get("/api/v1/health")

print("status:", response.status_code)
for key in [
    "X-XSS-Protection",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Strict-Transport-Security",
]:
    print(f"{key}: {response.headers.get(key)}")
PY
```

期望结果：
- `status: 200`
- `X-XSS-Protection: 1; mode=block`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security: None`

说明：按本轮设计，HSTS 不在后端直连 API 上返回，只在前端 HTTPS/TLS 终止点返回。

### Frontend Runtime: 页面 / 静态资源 / HTTPS HSTS

```bash
bash -lc '
set -euo pipefail
TMP_DIR=$(mktemp -d)
CONTAINER_NAME=codex-local-security-smoke
cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cat >"$TMP_DIR/openssl.cnf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = req_distinguished_name
x509_extensions = v3_req

[req_distinguished_name]
CN = 127.0.0.1

[v3_req]
subjectAltName = @alt_names

[alt_names]
IP.1 = 127.0.0.1
EOF

openssl req -x509 -nodes -days 7 -newkey rsa:2048 \
  -keyout "$TMP_DIR/key.pem" \
  -out "$TMP_DIR/cert.pem" \
  -config "$TMP_DIR/openssl.cnf" >/dev/null 2>&1

sed -e "s/listen 80;/listen 18081;/" \
    -e "s/listen 443 ssl;/listen 18443 ssl;/" \
    -e "s#proxy_pass http://requirement-backend:443;#proxy_pass http://127.0.0.1:1;#g" \
    frontend/nginx.internal.conf > "$TMP_DIR/nginx.conf"

docker run -d --name "$CONTAINER_NAME" --network host \
  -v "$TMP_DIR/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$TMP_DIR:/etc/nginx/ssl:ro" \
  -v "$PWD/frontend/build:/usr/share/nginx/html:ro" \
  nginx:latest >/dev/null

for _ in $(seq 1 20); do
  if curl -fsS -I http://127.0.0.1:18081/ >/dev/null 2>&1 && \
     curl -kfsS -I https://127.0.0.1:18443/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

ASSET_PATH=$(find frontend/build/assets -type f | head -n 1 | sed "s#^frontend/build##")

echo "=== HTTP / ==="
curl -sSI http://127.0.0.1:18081/ | grep -Ei "^(HTTP/|X-XSS-Protection:|X-Frame-Options:|X-Content-Type-Options:|Strict-Transport-Security:)"
echo "=== HTTP ${ASSET_PATH} ==="
curl -sSI "http://127.0.0.1:18081${ASSET_PATH}" | grep -Ei "^(HTTP/|X-XSS-Protection:|X-Frame-Options:|X-Content-Type-Options:|Strict-Transport-Security:)"
echo "=== HTTPS / ==="
curl -ksSI https://127.0.0.1:18443/ | grep -Ei "^(HTTP/|X-XSS-Protection:|X-Frame-Options:|X-Content-Type-Options:|Strict-Transport-Security:)"
'
```

期望结果：
- `HTTP /` 返回 `200`，且包含 `X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options`
- `HTTP /assets/...` 返回 `200`，且包含上述 3 个通用安全头
- `HTTPS /` 返回 `200`，且除上述 3 个通用安全头外，还包含 `Strict-Transport-Security: max-age=16070400`

说明：这里把 `/api/` 代理目标替换为 `127.0.0.1:1`，是为了在开发机只复测页面、静态资源和 HTTPS/HSTS 头，不引入本地后端网络接线噪声；该命令不用于验证代理链路可达性。

### Certificate Fallback: 自签名证书 SAN

```bash
python - <<'PY'
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

root = Path(".").resolve()
script = root / "deploy-frontend-internal.sh"

with tempfile.TemporaryDirectory() as ssl_dir:
    env = os.environ.copy()
    env["PROJECT_DIR"] = str(root)
    env["FRONTEND_SSL_DIR"] = ssl_dir
    env["FRONTEND_CERT_IPS"] = "8.153.194.178,10.62.16.251"
    command = textwrap.dedent(f"""
    set -e
    source "{script}"
    ensure_https_certificate_materials
    openssl x509 -in "{ssl_dir}/cert.pem" -noout -text | grep -A1 "Subject Alternative Name"
    """)
    result = subprocess.run(
        ["bash", "-lc", command],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    print(result.stdout)
PY
```

期望结果：
- 输出包含 `IP Address:8.153.194.178`
- 输出包含 `IP Address:10.62.16.251`
- 若目录中预先放入 `cert.pem` / `key.pem`，脚本不覆盖已有证书

### 本轮实测结论

- `2026-04-25` 已在当前开发机重跑上述口径，后端 `TestClient` 验证到 `/api/v1/health` 返回 3 个通用安全头，且无 HSTS。
- `2026-04-25` 已通过临时 nginx 容器验证：`HTTP /`、`HTTP /assets/...` 返回 3 个通用安全头，`HTTPS /` 额外返回 `Strict-Transport-Security: max-age=16070400`。
- `2026-04-25` 已通过 `ensure_https_certificate_materials + openssl x509 -text` 复核自签名证书 SAN，确认包含 `8.153.194.178` 与 `10.62.16.251`。
