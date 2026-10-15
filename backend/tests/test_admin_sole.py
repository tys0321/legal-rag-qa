"""唯一管理员 tys：免律师认证 + 不可再授予他人 admin。"""
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


def test_cannot_grant_other_admin(client: TestClient) -> None:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")

    sole = user_repo.get_user_by_username("tys")
    if not sole:
        sole = user_repo.create_user("tys", "pass1234")
        assert sole
    db.execute("UPDATE users SET role = 'admin' WHERE username = 'tys'")

    other = user_repo.create_user(f"u_{uuid.uuid4().hex[:8]}", "pass1234")
    assert other

    app.dependency_overrides[get_current_user] = lambda: {
        "id": sole["id"],
        "username": "tys",
        "role": "admin",
    }
    app.dependency_overrides[require_admin] = lambda: {
        "id": sole["id"],
        "username": "tys",
        "role": "admin",
    }
    resp = client.post(f"/api/admin/users/{other['id']}/set-role?role=admin", json={})
    assert resp.status_code == 400
    assert "tys" in resp.json().get("error", "")
