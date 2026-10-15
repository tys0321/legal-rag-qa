"""M4.1：法规检索 API（混合检索链路）。"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    def _fake_user() -> dict:
        return {"id": 1, "username": "tester", "role": "user"}

    app.dependency_overrides[get_current_user] = _fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_laws_search_requires_auth() -> None:
    # 无 override 时未登录应 401
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        resp = c.get("/api/laws/search", params={"q": "劳动合同"})
    assert resp.status_code == 401


def test_laws_search_hybrid_mocked(client: TestClient) -> None:
    fake = [
        {
            "id": "doc1#0",
            "doc_id": "doc1",
            "title": "中华人民共和国劳动合同法",
            "category": "法律",
            "article": "第三十条",
            "page": 1,
            "text": "用人单位应当按照劳动合同约定和国家规定，向劳动者及时足额支付劳动报酬。",
            "score": 0.91,
            "match": "bm25+vector",
            "rrf_score": 0.03,
            "effective_status": "现行有效",
            "effective_detail": "",
            "bian": "",
            "chapter": "",
            "section": "",
        }
    ]
    with patch("app.api.search_api.hybrid_search", return_value=fake) as mocked:
        with patch("app.api.search_api.get_store") as gs:
            store = gs.return_value
            store.load.return_value = None
            resp = client.get("/api/laws/search", params={"q": "拖欠工资", "top_k": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["backend"] == "hybrid"
    assert body["total"] == 1
    assert body["items"][0]["title"] == "中华人民共和国劳动合同法"
    assert body["items"][0]["article"] == "第三十条"
    mocked.assert_called_once()
    assert mocked.call_args.kwargs.get("top_k") == 5


def test_laws_search_empty_query(client: TestClient) -> None:
    resp = client.get("/api/laws/search", params={"q": "   "})
    # Query 校验或业务层 400
    assert resp.status_code in (400, 422)
