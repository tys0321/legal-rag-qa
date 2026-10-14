"""M2：律师认证与免责确认 API。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import database as db
from app.repositories import lawyers as lawyer_repo


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client: TestClient, prefix: str = "lw") -> tuple[str, int]:
    name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["token"], body["user_id"]


def test_lawyer_apply_and_review(client: TestClient) -> None:
    token, uid = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/lawyer/apply/json",
        json={"license_no": "A123456789", "region": "北京市", "specialties": ["劳动用工"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "pending"
    assert resp.json()["access"] == "pending_readonly"

    # 提升为 admin 审核
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (uid,))
    resp = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True, "reason": ""},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    assert lawyer_repo.can_use_lawyer_write(uid) is True


def test_disclaimer_ack(client: TestClient) -> None:
    token, uid = _register(client, "disc")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/disclaimer/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["acked"] is False
    resp = client.post("/api/disclaimer/ack", headers=headers, json={})
    assert resp.status_code == 200
    assert lawyer_repo.has_disclaimer_ack(uid) is True
