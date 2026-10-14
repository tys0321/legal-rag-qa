"""M3.1：案源发布 → 匹配 → 认领 → 模拟中间号/站内信。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import database as db
from app.repositories import leads as lead_repo
from app.repositories.leads import mask_contact, match_score


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client: TestClient, prefix: str = "u") -> tuple[str, int]:
    name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["token"], body["user_id"]


def _approve_lawyer(client: TestClient, token: str, uid: int, *, region: str, specs: list[str]) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/lawyer/apply/json",
        json={"license_no": f"L{uid:08d}", "region": region, "specialties": specs},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (uid,))
    resp = client.post(
        f"/api/admin/lawyer/{uid}/review",
        json={"approve": True, "reason": ""},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    # 审核后仍是 admin；再标回 lawyer 角色以便贴近真实（admin 也可写）
    db.execute("UPDATE users SET role = 'lawyer' WHERE id = ?", (uid,))


def test_mask_contact() -> None:
    assert mask_contact("13812345678") == "138****5678"
    assert mask_contact("ab@example.com").startswith("ab")


def test_match_score_scene_and_region() -> None:
    lead = {"scene": "劳动用工", "region": "北京市朝阳区"}
    assert match_score(lead, ["劳动用工", "合同纠纷"], "北京市") >= 15.0
    assert match_score(lead, ["婚姻家事"], "上海市") < 5.0


def test_lead_closed_loop(client: TestClient) -> None:
    # 用户发需求
    u_token, u_uid = _register(client, "cu")
    u_headers = {"Authorization": f"Bearer {u_token}"}
    resp = client.post(
        "/api/leads",
        json={
            "title": "拖欠工资两个月",
            "summary": "公司拖欠工资两个月，已签劳动合同，求协助维权。",
            "scene": "劳动用工",
            "region": "北京市朝阳区",
            "contact": "13812345678",
            "publish": True,
        },
        headers=u_headers,
    )
    assert resp.status_code == 200, resp.text
    lead = resp.json()
    assert lead["status"] == "open"
    assert lead["contact_masked"] == "138****5678"
    lead_id = lead["id"]

    # 律师认证 + 匹配列表（场景+地区命中应靠前）
    l_token, l_uid = _register(client, "lw")
    _approve_lawyer(client, l_token, l_uid, region="北京市", specs=["劳动用工", "合同纠纷"])
    l_headers = {"Authorization": f"Bearer {l_token}"}

    resp = client.get("/api/leads?scope=plaza", headers=l_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert any(x["id"] == lead_id for x in items)
    hit = next(x for x in items if x["id"] == lead_id)
    assert hit["match_score"] >= 15.0

    # pending 不可认领
    p_token, p_uid = _register(client, "pend")
    p_headers = {"Authorization": f"Bearer {p_token}"}
    client.post(
        "/api/lawyer/apply/json",
        json={"license_no": "P0001", "region": "北京市", "specialties": ["劳动用工"]},
        headers=p_headers,
    )
    resp = client.post(f"/api/leads/{lead_id}/claim", headers=p_headers)
    assert resp.status_code == 403

    # 认领
    resp = client.post(f"/api/leads/{lead_id}/claim", headers=l_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "claimed"
    assert resp.json()["claimed_by"] == l_uid

    # 二次认领失败
    l2_token, l2_uid = _register(client, "lw2")
    _approve_lawyer(client, l2_token, l2_uid, region="北京市", specs=["劳动用工"])
    resp = client.post(
        f"/api/leads/{lead_id}/claim",
        headers={"Authorization": f"Bearer {l2_token}"},
    )
    assert resp.status_code == 400

    # 站内信
    resp = client.post(
        f"/api/leads/{lead_id}/contact",
        json={"channel": "inbox", "message": "您好，我是承办律师，方便电话沟通吗？"},
        headers=l_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "in_contact"
    assert any(e["event_type"] == "inbox" for e in body["events"])

    # 模拟中间号（再次联系可走 virtual_number）
    resp = client.post(
        f"/api/leads/{lead_id}/contact",
        json={"channel": "virtual_number", "message": ""},
        headers=l_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["virtual_number"].startswith("400-")
    assert any(e["event_type"] == "virtual_number" for e in body["events"])

    # 关闭
    resp = client.post(
        f"/api/leads/{lead_id}/status",
        json={"status": "closed"},
        headers=l_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "closed"

    # 用户可看自己的案源事件
    resp = client.get(f"/api/leads/{lead_id}", headers=u_headers)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == u_uid
    assert len(resp.json()["events"]) >= 4


def test_owner_cannot_claim_own(client: TestClient) -> None:
    token, uid = _register(client, "own")
    _approve_lawyer(client, token, uid, region="上海市", specs=["房屋租赁"])
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/leads",
        json={
            "title": "押金不退",
            "summary": "房东无故扣押金。",
            "scene": "房屋租赁",
            "region": "上海市浦东新区",
            "contact": "13900001111",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    lead_id = resp.json()["id"]
    resp = client.post(f"/api/leads/{lead_id}/claim", headers=headers)
    assert resp.status_code == 400


def test_tables_exist() -> None:
    assert db.query_one("SHOW TABLES LIKE 'leads'") is not None
    assert db.query_one("SHOW TABLES LIKE 'lead_events'") is not None
    # 烟测仓储
    assert lead_repo.make_virtual_number(1).startswith("400-")
