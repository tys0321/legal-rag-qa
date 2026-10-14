"""M3.2：轻量律所创建 / 邀请 / 所内案源可见。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import database as db


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client: TestClient, prefix: str = "f") -> tuple[str, int, str]:
    name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["token"], body["user_id"], name


def _approve_lawyer(client: TestClient, token: str, uid: int) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/lawyer/apply/json",
        json={"license_no": f"F{uid:08d}", "region": "北京市", "specialties": ["劳动用工"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (uid,))
    resp = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    db.execute("UPDATE users SET role = 'lawyer' WHERE id = ?", (uid,))


def test_create_firm_invite_and_firm_leads(client: TestClient) -> None:
    # 负责人
    owner_token, owner_uid, owner_name = _register(client, "fo")
    _approve_lawyer(client, owner_token, owner_uid)
    owner_h = {"Authorization": f"Bearer {owner_token}"}

    resp = client.post("/api/firms", json={"name": "示例联合律所"}, headers=owner_h)
    assert resp.status_code == 200, resp.text
    firm = resp.json()
    firm_id = firm["id"]
    assert firm["name"] == "示例联合律所"
    assert any(m["role"] == "owner" and m["user_id"] == owner_uid for m in firm["members"])

    # /auth/me 带律所
    resp = client.get("/api/auth/me", headers=owner_h)
    assert resp.status_code == 200
    me = resp.json()
    assert me["firm_id"] == firm_id
    assert me["firm_name"] == "示例联合律所"
    assert me["firm_role"] == "owner"

    # 成员（已认证律师）
    mem_token, mem_uid, mem_name = _register(client, "fm")
    _approve_lawyer(client, mem_token, mem_uid)
    mem_h = {"Authorization": f"Bearer {mem_token}"}

    resp = client.post(
        f"/api/firms/{firm_id}/members",
        json={"username": mem_name},
        headers=owner_h,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_id"] == mem_uid

    resp = client.get("/api/firms/me", headers=mem_h)
    assert resp.status_code == 200
    assert resp.json()["id"] == firm_id
    assert len(resp.json()["members"]) == 2

    # 用户发案源（firm_visible）
    u_token, _, _ = _register(client, "fu")
    u_h = {"Authorization": f"Bearer {u_token}"}
    resp = client.post(
        "/api/leads",
        json={
            "title": "所内共享案源",
            "summary": "劳动争议，希望律师团队协作。",
            "scene": "劳动用工",
            "region": "北京市",
            "contact": "13700001111",
            "firm_visible": True,
            "publish": True,
        },
        headers=u_h,
    )
    assert resp.status_code == 200, resp.text
    lead_id = resp.json()["id"]
    assert resp.json()["firm_visible"] is True

    # 负责人认领
    resp = client.post(f"/api/leads/{lead_id}/claim", headers=owner_h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "claimed"

    # 成员可在 firm scope 看到
    resp = client.get("/api/leads?scope=firm", headers=mem_h)
    assert resp.status_code == 200
    ids = [x["id"] for x in resp.json()["items"]]
    assert lead_id in ids

    # 成员可查看详情（含事件）
    resp = client.get(f"/api/leads/{lead_id}", headers=mem_h)
    assert resp.status_code == 200
    assert resp.json()["id"] == lead_id

    # 所外律师不可见详情（非 open）
    out_token, out_uid, _ = _register(client, "fx")
    _approve_lawyer(client, out_token, out_uid)
    out_h = {"Authorization": f"Bearer {out_token}"}
    resp = client.get(f"/api/leads/{lead_id}", headers=out_h)
    assert resp.status_code == 403

    resp = client.get("/api/leads?scope=firm", headers=out_h)
    assert resp.status_code == 200
    assert all(x["id"] != lead_id for x in resp.json()["items"])


def test_pending_cannot_create_firm(client: TestClient) -> None:
    token, _, _ = _register(client, "fp")
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/lawyer/apply/json",
        json={"license_no": "PEND001", "region": "上海市", "specialties": ["合同纠纷"]},
        headers=headers,
    )
    resp = client.post("/api/firms", json={"name": "待审不可建所"}, headers=headers)
    assert resp.status_code == 403


def test_cannot_join_two_firms(client: TestClient) -> None:
    t1, u1, n1 = _register(client, "a1")
    _approve_lawyer(client, t1, u1)
    h1 = {"Authorization": f"Bearer {t1}"}
    resp = client.post("/api/firms", json={"name": "甲所"}, headers=h1)
    assert resp.status_code == 200
    firm1 = resp.json()["id"]

    t2, u2, n2 = _register(client, "a2")
    _approve_lawyer(client, t2, u2)
    h2 = {"Authorization": f"Bearer {t2}"}
    resp = client.post("/api/firms", json={"name": "乙所"}, headers=h2)
    assert resp.status_code == 200

    # 把已有律所的人再邀请进甲所 → 失败
    resp = client.post(
        f"/api/firms/{firm1}/members",
        json={"username": n2},
        headers=h1,
    )
    assert resp.status_code == 400
