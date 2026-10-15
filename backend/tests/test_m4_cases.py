"""M4.2：类案检索 API（向量 + 案例特征过滤）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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


def test_cases_search_requires_auth() -> None:
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        resp = c.get("/api/cases/search", params={"q": "劳动争议"})
    assert resp.status_code == 401


def test_cases_search_vector_mocked(client: TestClient) -> None:
    fake = [
        {
            "id": "case1#0",
            "doc_id": "case1",
            "title": "最高人民法院关于审理劳动争议案件的解释",
            "category": "司法解释",
            "article": "",
            "page": 1,
            "text": "用人单位未及时足额支付劳动报酬的，劳动者可以解除劳动合同。",
            "score": 0.82,
        },
        {
            "id": "case2#0",
            "doc_id": "case2",
            "title": "某指导案例：加班费争议",
            "category": "案例",
            "article": "",
            "page": 0,
            "text": "指导案例摘要……",
            "score": 0.71,
        },
    ]
    store = MagicMock()
    store.search_cases.return_value = fake
    with patch("app.api.search_api.get_store", return_value=store):
        resp = client.get("/api/cases/search", params={"q": "拖欠工资", "top_k": 4})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["backend"] == "vector_cases"
    assert body["total"] == 2
    # 边界文案：明确不以「法院判决书原文」自称（PRD 5.3）
    assert "不展示为" in body["notice"] and "法院判决书原文" in body["notice"]
    assert "司法解释" in body["notice"]
    assert body["items"][0]["kind"] == "judicial_interp"
    assert body["items"][1]["kind"] == "guiding_case"
    store.search_cases.assert_called_once_with("拖欠工资", top_k=4)


def test_cases_search_empty_query(client: TestClient) -> None:
    resp = client.get("/api/cases/search", params={"q": "   "})
    assert resp.status_code in (400, 422)
