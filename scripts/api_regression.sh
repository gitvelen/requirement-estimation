#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:443}
ADMIN_API_KEY=${ADMIN_API_KEY:-}
SKIP_KNOWLEDGE=${SKIP_KNOWLEDGE:-0}
STRICT=${STRICT:-0}

pass() { echo "[PASS] $1"; }
warn() { echo "[WARN] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

http_code() {
  curl -sS -o /dev/null -w "%{http_code}" "$@"
}

# 1) 健康检查
code=$(http_code "$BASE_URL/api/v1/health")
if [[ "$code" == "200" ]]; then pass "health"; else fail "health -> $code"; fi

# 2) 任务列表
code=$(http_code "$BASE_URL/api/v1/requirement/tasks")
if [[ "$code" == "200" ]]; then pass "requirement/tasks"; else fail "requirement/tasks -> $code"; fi

# 3) 知识库接口（可选）
if [[ "$SKIP_KNOWLEDGE" != "1" ]]; then
  code=$(http_code "$BASE_URL/api/v1/knowledge/stats")
  if [[ "$code" == "200" ]]; then pass "knowledge/stats"; else
    if [[ "$STRICT" == "1" ]]; then fail "knowledge/stats -> $code"; else warn "knowledge/stats -> $code"; fi
  fi

  code=$(http_code "$BASE_URL/api/v1/knowledge/evaluation-metrics")
  if [[ "$code" == "200" ]]; then pass "knowledge/evaluation-metrics"; else
    if [[ "$STRICT" == "1" ]]; then fail "knowledge/evaluation-metrics -> $code"; else warn "knowledge/evaluation-metrics -> $code"; fi
  fi
fi

# 4) 鉴权接口（可选）
if [[ -n "$ADMIN_API_KEY" ]]; then
  code=$(http_code -X POST -H "X-API-Key: $ADMIN_API_KEY" "$BASE_URL/api/v1/system/reload")
  if [[ "$code" == "200" ]]; then pass "system/reload (auth)"; else
    if [[ "$STRICT" == "1" ]]; then fail "system/reload (auth) -> $code"; else warn "system/reload (auth) -> $code"; fi
  fi
else
  warn "ADMIN_API_KEY 未设置，跳过鉴权接口测试"
fi

pass "api regression finished"
