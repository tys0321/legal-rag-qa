"""M6：合同审查 P2 占位。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "tester",
        "role": "user",
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_status_coming_soon(client: TestClient) -> None:
    resp = client.get("/api/contracts/review/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["status"] == "coming_soon"
    assert "P2" in body["message"] or "尚未开放" in body["message"]
    assert len(body["planned_features"]) >= 1


def test_review_not_implemented(client: TestClient) -> None:
    resp = client.post(
        "/api/contracts/review",
        json={"title": "租赁合同", "text": "甲方乙方约定租金……", "focus": "违约金"},
    )
    assert resp.status_code == 501
    assert "error" in resp.json()
