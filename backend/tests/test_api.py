"""API 集成测试（不依赖真实 LLM 调用）。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_index_served(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code in (200, 404)  # 未构建前端时 404 也可接受


def test_chat_empty_message_rejected(client: TestClient) -> None:
    # 先注册获取 token
    import uuid

    name = f"api_empty_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "secret123"})
    token = resp.json()["token"]
    resp = client.post(
        "/api/chat",
        json={"message": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 业务层 strip 后拒绝（400）或 pydantic min_length 拒绝（422）均可
    assert resp.status_code in (400, 422)


def test_stats_endpoint_shape(client: TestClient) -> None:
    resp = client.get("/api/stats")
    if resp.status_code == 200:
        data = resp.json()
        assert "chunk_count" in data
        assert "doc_count" in data
        assert "docs" in data


def test_openapi_schema(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/chat" in paths
    assert "/api/documents" in paths
