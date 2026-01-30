#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

MODE = os.getenv("MODE", "http").strip().lower()
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:443").rstrip("/")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()
TIMEOUT = float(os.getenv("TIMEOUT", "10"))

_client = None
if MODE == "testclient":
    from fastapi.testclient import TestClient
    from backend.app import app

    _client = TestClient(app)


def request(method, path, payload=None, headers=None):
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if MODE == "testclient":
        response = _client.request(method, path, json=payload, headers=req_headers)
        return response.status_code, response.text

    url = f"{BASE_URL}{path}"
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def parse_json(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def ensure_user(username, display_name, roles):
    if not ADMIN_API_KEY:
        raise RuntimeError("ADMIN_API_KEY 未配置，无法创建/查询用户")
    payload = {
        "username": username,
        "displayName": display_name,
        "password": "ChangeMe123!",
        "roles": roles,
        "email": f"{username}@example.com",
        "department": "integration",
        "isActive": True,
    }
    code, raw = request("POST", "/api/v1/users", payload, headers={"X-API-Key": ADMIN_API_KEY})
    if code == 200:
        return parse_json(raw).get("data")
    if code == 400 and "用户名已存在" in raw:
        list_code, list_raw = request("GET", "/api/v1/users", headers={"X-API-Key": ADMIN_API_KEY})
        if list_code == 200:
            users = parse_json(list_raw).get("data", [])
            for item in users:
                if item.get("username") == username:
                    return item
    raise RuntimeError(f"创建用户失败 ({code}): {raw}")


def login(username, password):
    code, raw = request("POST", "/api/v1/auth/login", {"username": username, "password": password})
    if code != 200:
        raise RuntimeError(f"登录失败 ({code}): {raw}")
    return parse_json(raw).get("data", {}).get("token")


def auth_get(path, token):
    return request("GET", path, headers={"Authorization": f"Bearer {token}"})


def main():
    code, raw = request("GET", "/api/v1/health")
    if code != 200:
        print(f"[FAIL] health -> {code} {raw}")
        return 1
    print("[PASS] health")

    admin = ensure_user("integration_admin", "集成管理员", ["admin"])
    manager = ensure_user("integration_manager", "集成经理", ["manager"])
    expert = ensure_user("integration_expert", "集成专家", ["expert"])
    print("[PASS] users ready")

    manager_token = login(manager["username"], "ChangeMe123!")
    admin_token = login(admin["username"], "ChangeMe123!")
    print("[PASS] login")

    code, raw = auth_get("/api/v1/auth/me", manager_token)
    if code != 200:
        print(f"[FAIL] auth/me -> {code} {raw}")
        return 1
    print("[PASS] auth/me")

    code, raw = auth_get("/api/v1/tasks", manager_token)
    if code != 200:
        print(f"[FAIL] tasks (manager) -> {code} {raw}")
        return 1
    print("[PASS] tasks (manager)")

    code, raw = auth_get("/api/v1/tasks?scope=all", admin_token)
    if code != 200:
        print(f"[FAIL] tasks (admin) -> {code} {raw}")
        return 1
    print("[PASS] tasks (admin)")

    code, raw = auth_get("/api/v1/notifications/unread-count", admin_token)
    if code != 200:
        print(f"[FAIL] notifications/unread-count -> {code} {raw}")
        return 1
    print("[PASS] notifications/unread-count")

    print("[PASS] integration smoke finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
