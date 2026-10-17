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


def test_admin_can_view_files_and_revoke(client: TestClient) -> None:
    from app.api.lawyer_api import CERT_DIR

    admin_token, admin_uid = _register(client, "adm")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (admin_uid,))

    token, uid = _register(client, "cert")
    headers = {"Authorization": f"Bearer {token}"}
    cert_name = f"{uid}_demo.png"
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    (CERT_DIR / cert_name).write_bytes(b"\x89PNG\r\n\x1a\nfake")

    lawyer_repo.upsert_application(
        uid,
        license_no="B99887766",
        region="上海市",
        specialties=["合同纠纷"],
        license_files=[cert_name],
    )

    pending = client.get("/api/admin/lawyer/pending", headers=admin_headers)
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert any(i["user_id"] == uid and cert_name in i.get("license_files", []) for i in items)

    file_resp = client.get(f"/api/admin/lawyer/{uid}/files/{cert_name}", headers=admin_headers)
    assert file_resp.status_code == 200, file_resp.text
    assert file_resp.content.startswith(b"\x89PNG")

    approve = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True, "reason": ""},
        headers=admin_headers,
    )
    assert approve.status_code == 200
    approved = client.get("/api/admin/lawyer/approved", headers=admin_headers)
    assert approved.status_code == 200
    assert any(i["user_id"] == uid for i in approved.json()["items"])
    assert lawyer_repo.can_use_lawyer_write(uid) is True

    revoke = client.post(
        f"/api/admin/lawyer/{uid}/revoke",
        json={"reason": "测试撤销"},
        headers=admin_headers,
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["status"] == "rejected"
    assert lawyer_repo.can_use_lawyer_write(uid) is False
    approved_after = client.get("/api/admin/lawyer/approved", headers=admin_headers)
    assert not any(i["user_id"] == uid for i in approved_after.json()["items"])


def test_disclaimer_ack(client: TestClient) -> None:
    token, uid = _register(client, "disc")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/disclaimer/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["acked"] is False
    resp = client.post("/api/disclaimer/ack", headers=headers, json={})
    assert resp.status_code == 200
    assert lawyer_repo.has_disclaimer_ack(uid) is True
