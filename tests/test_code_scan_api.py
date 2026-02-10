import io
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import code_scan_service
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

    monkeypatch.delenv("CODE_SCAN_REPO_ALLOWLIST", raising=False)
    monkeypatch.delenv("CODE_SCAN_GIT_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("CODE_SCAN_ENABLE_GIT_URL", "false")
    monkeypatch.setenv("CODE_SCAN_ARCHIVE_MAX_BYTES", str(300 * 1024 * 1024))
    monkeypatch.setenv("CODE_SCAN_ARCHIVE_MAX_FILES", "20000")

    code_scan_service._code_scan_service = None
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


def _create_repo(base_dir: Path, name: str = "hop-repo") -> str:
    repo_dir = base_dir / "repos" / name
    java_dir = repo_dir / "src" / "main" / "java" / "demo"
    java_dir.mkdir(parents=True, exist_ok=True)
    java_file = java_dir / "DemoController.java"
    java_file.write_text(
        """
package demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class DemoController {

    @GetMapping("/api/demo/query")
    public String query() {
        return "ok";
    }
}
        """.strip(),
        encoding="utf-8",
    )
    return str(repo_dir.resolve())


def _wait_job_completed(client: TestClient, token: str, job_id: str, timeout_sec: float = 8.0):
    start = time.time()
    while time.time() - start < timeout_sec:
        response = client.get(
            f"/api/v1/code-scan/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} not finished in {timeout_sec}s")


def test_code_scan_local_idempotency_and_force(client):
    owner = _seed_user("owner", "owner123", ["manager"])
    token = _login(client, "owner", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])
    repo_path = _create_repo(Path(settings.REPORT_DIR), "repo-idempotent")

    payload = {
        "system_name": "HOP",
        "system_id": "sys_hop",
        "repo_path": repo_path,
        "options": {"paths": ["src/main/java"]},
    }

    first = client.post("/api/v1/code-scan/jobs", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200
    first_job = first.json()

    second = client.post("/api/v1/code-scan/jobs", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    second_job = second.json()
    assert second_job["job_id"] == first_job["job_id"]

    forced = client.post(
        "/api/v1/code-scan/jobs",
        json={**payload, "force": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forced.status_code == 200
    forced_job = forced.json()
    assert forced_job["job_id"] != first_job["job_id"]


def test_code_scan_path_not_allowlist_returns_scan004(client, tmp_path):
    owner = _seed_user("owner2", "owner123", ["manager"])
    token = _login(client, "owner2", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])

    outside = tmp_path / "outside_repo"
    (outside / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)

    response = client.post(
        "/api/v1/code-scan/jobs",
        json={"system_name": "HOP", "system_id": "sys_hop", "repo_path": str(outside.resolve())},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_scan_allowlist"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "SCAN_004"
    assert payload["request_id"] == "req_scan_allowlist"


def test_code_scan_git_disabled_returns_scan001(client):
    owner = _seed_user("owner3", "owner123", ["manager"])
    token = _login(client, "owner3", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])

    response = client.post(
        "/api/v1/code-scan/jobs",
        json={
            "system_name": "HOP",
            "system_id": "sys_hop",
            "repo_path": "https://git.example.com/core/hop.git",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SCAN_001"


def test_code_scan_invalid_archive_returns_scan005(client):
    owner = _seed_user("owner4", "owner123", ["manager"])
    token = _login(client, "owner4", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])

    response = client.post(
        "/api/v1/code-scan/jobs",
        data={"system_name": "HOP", "system_id": "sys_hop"},
        files={"repo_archive": ("repo.zip", b"not-a-valid-archive", "application/zip")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SCAN_005"


def test_code_scan_archive_over_limit_returns_scan006(client, monkeypatch):
    owner = _seed_user("owner5", "owner123", ["manager"])
    token = _login(client, "owner5", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])

    monkeypatch.setenv("CODE_SCAN_ARCHIVE_MAX_FILES", "1")
    code_scan_service._code_scan_service = None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("repo/src/main/java/A.java", "class A {}")
        zf.writestr("repo/src/main/java/B.java", "class B {}")

    response = client.post(
        "/api/v1/code-scan/jobs",
        data={"system_name": "HOP", "system_id": "sys_hop"},
        files={"repo_archive": ("repo.zip", buf.getvalue(), "application/zip")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SCAN_006"


def test_code_scan_ingest_idempotent_and_profile_completeness(client):
    owner = _seed_user("owner6", "owner123", ["manager"])
    token = _login(client, "owner6", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])
    repo_path = _create_repo(Path(settings.REPORT_DIR), "repo-ingest")

    create_resp = client.post(
        "/api/v1/code-scan/jobs",
        json={"system_name": "HOP", "system_id": "sys_hop", "repo_path": repo_path},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["job_id"]

    service = code_scan_service.get_code_scan_service()
    service.embedding_service = DummyEmbeddingService()

    final_job = _wait_job_completed(client, token, job_id)
    assert final_job["status"] == "completed"

    first_ingest = client.post(
        f"/api/v1/code-scan/jobs/{job_id}/ingest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_ingest.status_code == 200
    ingest_payload = first_ingest.json()
    assert ingest_payload["failed"] == 0
    assert ingest_payload["success"] >= 1

    second_ingest = client.post(
        f"/api/v1/code-scan/jobs/{job_id}/ingest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_ingest.status_code == 200
    second_payload = second_ingest.json()
    assert second_payload["success"] == 0
    assert second_payload["failed"] == 0

    profile_service = system_profile_service.get_system_profile_service()
    profile = profile_service.get_profile("HOP")
    assert profile
    assert profile.get("completeness", {}).get("code_scan") is True
    assert int(profile.get("completeness_score") or 0) >= 30


def test_code_scan_ingest_embedding_unavailable_returns_emb001(client):
    owner = _seed_user("owner7", "owner123", ["manager"])
    token = _login(client, "owner7", "owner123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])
    repo_path = _create_repo(Path(settings.REPORT_DIR), "repo-emb-fail")

    create_resp = client.post(
        "/api/v1/code-scan/jobs",
        json={"system_name": "HOP", "system_id": "sys_hop", "repo_path": repo_path},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["job_id"]

    _wait_job_completed(client, token, job_id)

    service = code_scan_service.get_code_scan_service()
    service.embedding_service = BrokenEmbeddingService()

    ingest_resp = client.post(
        f"/api/v1/code-scan/jobs/{job_id}/ingest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ingest_resp.status_code == 503
    payload = ingest_resp.json()
    assert payload["error_code"] == "EMB_001"

    profile_service = system_profile_service.get_system_profile_service()
    profile = profile_service.get_profile("HOP")
    assert not profile or not profile.get("completeness", {}).get("code_scan")


def test_code_scan_owner_and_creator_permission(client):
    owner = _seed_user("owner8", "owner123", ["manager"])
    other = _seed_user("other8", "other123", ["manager"])

    owner_token = _login(client, "owner8", "owner123")
    other_token = _login(client, "other8", "other123")

    _seed_system_owner("HOP", "sys_hop", owner["id"])
    repo_path = _create_repo(Path(settings.REPORT_DIR), "repo-auth")

    denied_submit = client.post(
        "/api/v1/code-scan/jobs",
        json={"system_name": "HOP", "system_id": "sys_hop", "repo_path": repo_path},
        headers={"Authorization": f"Bearer {other_token}", "X-Request-ID": "req_scan_auth"},
    )
    assert denied_submit.status_code == 403
    denied_payload = denied_submit.json()
    assert denied_payload["error_code"] == "AUTH_001"
    assert denied_payload["request_id"] == "req_scan_auth"

    create_resp = client.post(
        "/api/v1/code-scan/jobs",
        json={"system_name": "HOP", "system_id": "sys_hop", "repo_path": repo_path},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["job_id"]

    denied_get = client.get(
        f"/api/v1/code-scan/jobs/{job_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied_get.status_code == 403
    assert denied_get.json()["error_code"] == "AUTH_001"
