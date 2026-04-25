from fastapi.testclient import TestClient

from backend.app import app


REQUIRED_SECURITY_HEADERS = {
    "X-XSS-Protection": "1; mode=block",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
}


def test_health_endpoint_returns_required_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200

    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert response.headers.get(header_name) == expected_value
