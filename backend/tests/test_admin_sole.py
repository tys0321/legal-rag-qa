"""根管理员 tys：可授予/撤销次级管理员，并限制其权限。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user, require_admin
from app.main import app
from app.repositories import database as db
from app.repositories import lawyers as lawyer_repo
from app.repositories import users as user_repo


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _as(user: dict) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user


def test_admin_skips_lawyer_cert() -> None:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")
    name = f"adm_{uuid.uuid4().hex[:8]}"
    u = user_repo.create_user(name, "pass1234")
    assert u
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (u["id"],))
    assert lawyer_repo.lawyer_mode_access(u["id"]) == "approved"
    assert lawyer_repo.can_use_lawyer_write(u["id"]) is True
    assert lawyer_repo.has_disclaimer_ack(u["id"]) is True


def test_tys_grant_and_revoke_admin(client: TestClient) -> None:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")

    sole = user_repo.get_user_by_username("tys")
    if not sole:
        sole = user_repo.create_user("tys", "pass1234")
        assert sole
    db.execute("UPDATE users SET role = 'admin' WHERE username = 'tys'")
    sole = user_repo.get_user_by_username("tys")
    assert sole

    other = user_repo.create_user(f"u_{uuid.uuid4().hex[:8]}", "pass1234")
    assert other
    _as({"id": sole["id"], "username": "tys", "role": "admin"})

    granted = client.post(
        f"/api/admin/users/{other['id']}/set-role?role=admin",
        json={"permissions": ["feedbacks", "logs"]},
    )
    assert granted.status_code == 200, granted.text
    row = db.query_one("SELECT role, admin_perms FROM users WHERE id = ?", (other["id"],))
    assert row["role"] == "admin"
    assert "feedbacks" in str(row["admin_perms"])

    third = user_repo.create_user(f"u_{uuid.uuid4().hex[:8]}", "pass1234")
    assert third
    # 次级管理员不能再授权，也不能看未分配的用户管理
    _as({"id": other["id"], "username": other["username"], "role": "admin", "admin_perms": ["feedbacks", "logs"]})
    denied = client.post(
        f"/api/admin/users/{third['id']}/set-role?role=admin",
        json={"permissions": ["logs"]},
    )
    assert denied.status_code == 403
    users = client.get("/api/admin/users")
    assert users.status_code == 403

    _as({"id": sole["id"], "username": "tys", "role": "admin"})
    revoked = client.post(f"/api/admin/users/{other['id']}/set-role?role=user", json={})
    assert revoked.status_code == 200, revoked.text
    again = db.query_one("SELECT role, admin_perms FROM users WHERE id = ?", (other["id"],))
    assert again["role"] == "user"
    assert not again["admin_perms"]
