import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import esb_service
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


class BrokenEmbeddingService:
    def generate_embedding(self, text):
        raise RuntimeError("embedding unavailable")

    def batch_generate_embeddings(self, texts, batch_size=25):
        raise RuntimeError("embedding unavailable")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    esb_service._esb_service = None
    system_profile_service._system_profile_service = None

    return TestClient(app)


def _seed_user(username: str, password: str, roles):
    user = user_service.create_user_record(
        {
            "username": username,
            "display_name": username,
            "password": password,
            "roles": roles,
        }
    )
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _seed_system_owner(system_name: str, system_id: str, owner_id: str):
    system_routes._write_systems(
        [
            {
                "id": system_id,
                "name": system_name,
                "abbreviation": system_name,
                "status": "运行中",
                "extra": {"owner_id": owner_id},
            }
        ]
    )


def test_esb_import_requires_owner(client):
    owner = _seed_user("esb_owner", "owner123", ["manager"])
    other = _seed_user("esb_other", "other123", ["manager"])

    _seed_system_owner("HOP", "sys_hop", owner["id"])

    other_token = _login(client, "esb_other", "other123")

    csv_content = (
        "提供方系统简称,调用方系统简称,交易名称,状态\n"
        "sys_hop,sys_x,查询接口,正常使用\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/esb/imports",
        data={"system_id": "sys_hop"},
        files={"file": ("esb.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {other_token}", "X-Request-ID": "req_esb_auth"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error_code"] == "AUTH_001"
    assert payload["request_id"] == "req_esb_auth"


def test_esb_import_missing_required_columns_returns_esb002(client):
    owner = _seed_user("esb_owner2", "owner123", ["manager"])
    _seed_system_owner("HOP", "sys_hop", owner["id"])
    token = _login(client, "esb_owner2", "owner123")

    invalid_csv = (
        "系统,接口名\n"
        "sys_hop,查询\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/esb/imports",
        data={"system_id": "sys_hop"},
        files={"file": ("esb.csv", invalid_csv, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "ESB_002"


def test_esb_import_filters_by_system_id_and_updates_completeness(client):
    owner = _seed_user("esb_owner3", "owner123", ["manager"])
    _seed_system_owner("HOP", "sys_hop", owner["id"])
    token = _login(client, "esb_owner3", "owner123")

    service = esb_service.get_esb_service()
    service.embedding_service = DummyEmbeddingService()

    csv_content = (
        "提供方系统简称,调用方系统简称,交易名称,状态\n"
        "sys_hop,sys_x,查询接口,正常使用\n"
        "sys_other,sys_else,同步接口,正常使用\n"
    ).encode("utf-8")

    mapping_json = {
        "provider_system_id": ["提供方系统简称"],
        "consumer_system_id": ["调用方系统简称"],
        "service_name": "交易名称",
        "status": "状态",
    }

    response = client.post(
        "/api/v1/esb/imports",
        data={"system_id": "sys_hop", "mapping_json": str(mapping_json).replace("'", '"')},
        files={"file": ("esb.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 1
    assert payload["skipped"] >= 1

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert profile
    assert profile.get("completeness", {}).get("esb") is True
    assert int(profile.get("completeness_score") or 0) >= 30


def test_esb_import_embedding_unavailable_returns_emb001(client):
    owner = _seed_user("esb_owner4", "owner123", ["manager"])
    _seed_system_owner("HOP", "sys_hop", owner["id"])
    token = _login(client, "esb_owner4", "owner123")

    service = esb_service.get_esb_service()
    service.embedding_service = BrokenEmbeddingService()

    csv_content = (
        "提供方系统简称,调用方系统简称,交易名称,状态\n"
        "sys_hop,sys_x,查询接口,正常使用\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/esb/imports",
        data={"system_id": "sys_hop"},
        files={"file": ("esb.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == "EMB_001"

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert not profile or not profile.get("completeness", {}).get("esb")
