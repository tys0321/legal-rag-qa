"""M7：消息反馈（有用/无用）+ 管理端列表。"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user, require_admin
from app.main import app
from app.repositories import database as db
from app.repositories.sessions import SessionStore


def _as_user(user_id: int = 1, username: str = "tester", role: str = "user") -> None:
    user = {"id": user_id, "username": username, "role": role}
    app.dependency_overrides[get_current_user] = lambda: user
    if role == "admin":
        app.dependency_overrides[require_admin] = lambda: user
    else:
        app.dependency_overrides.pop(require_admin, None)


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _ensure_user(user_id: int = 1, username: str = "tester", role: str = "user") -> None:
    row = db.query_one("SELECT id FROM users WHERE id = ?", (user_id,))
    if row:
        return
    db.execute(
        "INSERT INTO users (id, username, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, "x", "y", role),
    )


def test_feedback_flow(client: TestClient) -> None:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")

    _ensure_user(1, "tester", "user")
    _ensure_user(99, "admin", "admin")

    store = SessionStore()
    sid = store.create(1, "反馈测试问题")
    store.append(sid, "user", "公司拖欠工资怎么办", 1)
    mid = store.append(sid, "assistant", "可依法申请劳动仲裁。", 1)
    assert mid

    _as_user(1, "tester", "user")
    bad = client.post(f"/api/chat/{mid}/feedback", json={"rating": "maybe"})
    assert bad.status_code == 400

    ok = client.post(
        f"/api/chat/{mid}/feedback",
        json={"rating": "useful", "comment": "有帮助"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["rating"] == "useful"

    ok2 = client.post(f"/api/chat/{mid}/feedback", json={"rating": "useless"})
    assert ok2.status_code == 200
    assert ok2.json()["rating"] == "useless"

    _as_user(99, "admin", "admin")
    lst = client.get("/api/admin/feedbacks?limit=20")
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body["total"] >= 1
    assert any(x["message_id"] == mid for x in body["items"])


def test_chat_returns_message_id(client: TestClient) -> None:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")
    _ensure_user(1, "tester", "user")
    _as_user(1, "tester", "user")

    fake = type(
        "R",
        (),
        {
            "answer": "测试回答",
            "mode": "fast",
            "sources": [],
            "disclaimer": "免责",
            "routed_reason": "fast",
            "related_cases": [],
            "confidence": "medium",
            "critic_issues": [],
            "risk_level": "L3",
            "risk_banner": "",
            "force_lawyer_cta": False,
            "scene": "",
            "need_slots": [],
            "waiting_for_slot": False,
        },
    )()
    with patch("app.api.chat.get_chat_service") as gs:
        svc = gs.return_value
        svc.ask.return_value = (fake, "abc123", 4242)
        resp = client.post("/api/chat", json={"message": "你好", "skip_slots": True})
    assert resp.status_code == 200
    assert resp.json()["message_id"] == 4242
