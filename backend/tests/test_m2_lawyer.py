"""M2：律师认证与免责确认 API。"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.admin_perms import PERM_KEYS
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


def _promote_admin(user_id: int) -> None:
    """测试用：设为次级管理员并授予全部板块权限。"""
    perms = json.dumps(sorted(PERM_KEYS), ensure_ascii=False)
    db.execute(
        "UPDATE users SET role = 'admin', admin_perms = ? WHERE id = ?",
        (perms, user_id),
    )


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

    # 提升为 admin 审核（需 lawyers 权限）
    _promote_admin(uid)
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
    _promote_admin(admin_uid)

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


def test_judge_apply_sets_role_and_blocks_lead_write(client: TestClient) -> None:
    """法官认证通过后 role=judge，不可接案源。"""
    admin_token, admin_uid = _register(client, "jadm")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _promote_admin(admin_uid)

    token, uid = _register(client, "judge")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/lawyer/apply/json",
        json={
            "profession": "judge",
            "license_no": "J20260001",
            "region": "北京市",
            "specialties": ["民商事"],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["profession"] == "judge"
    assert resp.json()["status"] == "pending"

    approve = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True, "reason": ""},
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["profession"] == "judge"
    assert approve.json()["status"] == "approved"

    row = db.query_one("SELECT role FROM users WHERE id = ?", (uid,))
    assert row and row["role"] == "judge"
    assert lawyer_repo.can_use_lawyer_write(uid) is False


def test_prosecutor_apply_and_role(client: TestClient) -> None:
    admin_token, admin_uid = _register(client, "padm")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _promote_admin(admin_uid)

    token, uid = _register(client, "proc")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/lawyer/apply/json",
        json={
            "profession": "prosecutor",
            "license_no": "P20260002",
            "region": "上海市",
            "specialties": ["刑事公诉"],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["profession"] == "prosecutor"

    approve = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True, "reason": ""},
        headers=admin_headers,
    )
    assert approve.status_code == 200
    row = db.query_one("SELECT role FROM users WHERE id = ?", (uid,))
    assert row and row["role"] == "prosecutor"
    assert lawyer_repo.can_use_lawyer_write(uid) is False


def test_disclaimer_ack(client: TestClient) -> None:
    token, uid = _register(client, "disc")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/disclaimer/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["acked"] is False
    resp = client.post("/api/disclaimer/ack", headers=headers, json={})
    assert resp.status_code == 200
    assert lawyer_repo.has_disclaimer_ack(uid) is True
