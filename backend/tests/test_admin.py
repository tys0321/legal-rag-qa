"""管理后台 API 测试：非 admin 403、admin 可访问。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client: TestClient, prefix: str = "adm") -> str:
    name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "abc12345"})
    assert resp.status_code == 200, resp.text
    return name, resp.json()["token"]


def test_admin_api_requires_admin(client: TestClient) -> None:
    # 未登录
    assert client.get("/api/admin/users").status_code == 401
    # 普通用户 403
    _, token = _register(client)
    assert client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.get("/api/admin/status", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_admin_api_works_for_admin(client: TestClient) -> None:
    # 登录内置 admin
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    r1 = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200
    users = r1.json()["users"]
    assert any(u["username"] == "admin" and u["role"] == "admin" for u in users)

    r2 = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert "user_count" in r2.json()

    r3 = client.get("/api/admin/status", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert "chat_model" in r3.json()


def test_backup_api_requires_admin(client: TestClient) -> None:
    _, token = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/admin/backup/list", headers=h).status_code == 403
    assert client.post("/api/admin/backup/create", headers=h).status_code == 403


def test_backup_create_list_restore_delete(client: TestClient) -> None:
    """快照 API 全流程：创建 → 列表 → 恢复 → 删除。"""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    # 创建
    r = client.post("/api/admin/backup/create", params={"description": "pytest快照"}, headers=h)
    assert r.status_code == 200, r.text
    name = r.json()["name"]
    assert name.startswith("snapshot_")

    # 列表
    r = client.get("/api/admin/backup/list", headers=h)
    assert r.status_code == 200
    names = [s["name"] for s in r.json()["snapshots"]]
    assert name in names

    # 恢复
    r = client.post(f"/api/admin/backup/{name}/restore", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # 删除
    r = client.delete(f"/api/admin/backup/{name}", headers=h)
    assert r.status_code == 200
    r = client.get("/api/admin/backup/list", headers=h)
    assert name not in [s["name"] for s in r.json()["snapshots"]]

    # 恢复不存在的快照 → 404
    r = client.post("/api/admin/backup/nonexistent/restore", headers=h)
    assert r.status_code == 404
