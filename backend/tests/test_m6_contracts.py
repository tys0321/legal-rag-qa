"""合同审查：已开放，返回备忘录草稿。"""
from __future__ import annotations

from unittest.mock import patch

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


def test_status_open(client: TestClient) -> None:
    resp = client.get("/api/contracts/review/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["status"] == "active"


def test_review_returns_draft(client: TestClient) -> None:
    md = """## 风险点
- 违约金过高

## 法规对照
对照 [1]

## 审查备忘录
建议律师复核

## 免责声明
须律师审核
"""
    hits = [
        {
            "id": "d1#0",
            "doc_id": "d1",
            "title": "中华人民共和国民法典",
            "category": "法律",
            "article": "第五百八十五条",
            "page": 1,
            "text": "约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。",
            "score": 0.8,
        }
    ]
    with (
        patch("app.services.contract_review.get_store") as store,
        patch("app.services.contract_review.chat", return_value=md),
    ):
        store.return_value.search.return_value = hits
        resp = client.post(
            "/api/contracts/review",
            json={"title": "租赁合同", "text": "甲方乙方约定租金与违约金。", "focus": "违约金"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert any("违约金" in x for x in body["findings"])
    assert body["sources"]
