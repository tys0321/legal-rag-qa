"""用户鉴权与会话隔离测试（含注册约束校验）。"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _uname(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register(client: TestClient, username: str, password: str = "secret123") -> str:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def test_register_and_login(client: TestClient) -> None:
    name = _uname("tuser")
    token = _register(client, name)
    assert token
    # 重复注册失败
    resp = client.post("/api/auth/register", json={"username": name, "password": "secret123"})
    assert resp.status_code == 409
    # 登录
    resp = client.post("/api/auth/login", json={"username": name, "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["token"]
    # 错误密码
    resp = client.post("/api/auth/login", json={"username": name, "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "username,password,reason",
    [
        ("", "secret123", "用户名空"),
        ("   ", "secret123", "用户名全空格"),
        ("a", "secret123", "用户名过短"),
        ("okuser", "", "密码空"),
        ("okuser", "abcdef", "纯字母无数字"),
        ("okuser", "123456", "纯数字无字母"),
        ("okuser", "abc", "密码过短"),
    ],
)
def test_register_rejects_invalid(client: TestClient, username: str, password: str, reason: str) -> None:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    # pydantic 校验失败返回 422，业务层 UserError 返回 400，均视为拒绝
    assert resp.status_code in (400, 422), f"{reason} 应被拒绝: {resp.text}"


def test_register_accepts_valid_password(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"username": _uname("ok"), "password": "Abc12345"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "user"


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    name = _uname("tuser")
    token = _register(client, name)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == name
    assert resp.json()["role"] == "user"


def test_sessions_isolated_between_users(client: TestClient) -> None:
    t1 = _register(client, _uname("isoa"))
    t2 = _register(client, _uname("isob"))

    # A 创建会话并提问
    resp = client.post(
        "/api/chat",
        json={"message": "你好", "session_id": None},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 200
    sid = resp.json()["session_id"]

    # A 能看到自己的会话
    resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {t1}"})
    assert resp.status_code == 200
    assert any(s["id"] == sid for s in resp.json()["sessions"])

    # B 看不到 A 的会话
    resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {t2}"})
    assert resp.status_code == 200
    assert not any(s["id"] == sid for s in resp.json()["sessions"])

    # B 无法读取 A 的会话消息
    resp = client.get(f"/api/sessions/{sid}/messages", headers={"Authorization": f"Bearer {t2}"})
    assert resp.status_code == 404

    # B 无法删除 A 的会话
    resp = client.delete(f"/api/sessions/{sid}", headers={"Authorization": f"Bearer {t2}"})
    assert resp.status_code == 404

    # A 可以删除
    resp = client.delete(f"/api/sessions/{sid}", headers={"Authorization": f"Bearer {t1}"})
    assert resp.status_code == 200


def test_chat_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/chat", json={"message": "你好", "session_id": None})
    assert resp.status_code == 401


def test_batch_delete_sessions(client: TestClient) -> None:
    """批量删除会话：只删自己的，且只删存在的。"""
    t1 = _register(client, _uname("batcha"))
    t2 = _register(client, _uname("batchb"))

    # A 创建 3 个会话
    ids = []
    for msg in ("会话一", "会话二", "会话三"):
        resp = client.post(
            "/api/chat",
            json={"message": msg, "session_id": None},
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert resp.status_code == 200
        ids.append(resp.json()["session_id"])

    # 批量删除 2 个（含一个不存在的 id 和一个属于 B 的 id）
    resp = client.post(
        "/api/sessions/batch-delete",
        json={"session_ids": ids[:2] + ["not_exist_id", "foreign"]},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 200
    assert resp.json()["removed"] == 2  # 只删掉 A 自己的 2 个

    # 剩余 1 个
    resp = client.get("/api/sessions", headers={"Authorization": f"Bearer {t1}"})
    remaining = resp.json()["sessions"]
    assert len(remaining) == 1
    assert remaining[0]["id"] == ids[2]

    # 空列表 → 拒绝
    resp = client.post(
        "/api/sessions/batch-delete",
        json={"session_ids": []},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 422
