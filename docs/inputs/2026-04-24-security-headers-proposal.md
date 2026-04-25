# 安全响应头整改输入

## intent

安全团队在测试环境扫描后，指出当前 Web 应用缺失 4 项安全响应头：

1. `X-XSS-Protection`
2. `X-Frame-Options`
3. `Strict-Transport-Security`
4. `X-Content-Type-Options`

用户要求为此发起一个新的项目变更。当前阶段为 Proposal，目标是在不破坏现有访问方式的前提下，明确整改范围、边界、默认口径和后续复测路径，并以后续通过安全团队复测为导向推进。

## local-observations

- 本地代码核查显示，`backend/app.py` 当前未统一下发上述安全响应头。
- 本地代码核查显示，`frontend/nginx.conf`、`frontend/nginx.internal.conf`、`frontend/nginx-remote.conf` 当前也未统一配置上述安全响应头。
- 当前安全团队命中的测试环境入口为 `http://10.62.16.251:8000`。

## clarifications

### retest-goal

这四个问题都需要整改，并以后续通过安全团队复测为目标。

### access-mode

当前典型使用场景是若干台 Windows 机器打开浏览器后，直接输入 IP 访问系统；当前没有可依赖的内网域名。

### compatibility

整改方案需要充分测试，不能把现有系统访问改坏。

### external-ip

外网测试场景下，用户也习惯直接通过 IP 访问，例如 `http://8.153.194.178/`；后续方案不能让用户输入 IP 后直接不可访问。

### hsts-default

对于第 3 项，如果没有更好的路径，可先采纳安全团队建议：目标头值为 `Strict-Transport-Security: max-age=16070400`，并按对方提示将“需要 HTTPS/443 Web 服务器前提”纳入后续方案评估与验证。

### cert-bootstrap

为避免其他环境部署时因缺少现成 HTTPS 证书而阻塞，允许安装/部署脚本在 `cert.pem` / `key.pem` 缺失时自动生成仅供该环境使用的自签名证书；生成的证书必须覆盖目标访问 IP，但本轮不扩展到浏览器根证书分发或受信任 CA 接入。
