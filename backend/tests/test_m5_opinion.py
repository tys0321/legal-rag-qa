"""M5.1：法律意见书生成。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.services.opinion import _parse_sections, generate_opinion


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


def test_parse_sections() -> None:
    md = """## 案情梳理
事实A

## 法律分析
分析B [1]

## 行动建议
1. 做C

## 免责声明
免责D
"""
    sec = _parse_sections(md)
    assert "事实A" in sec["case_summary"]
    assert "分析B" in sec["legal_analysis"]
    assert "做C" in sec["action_advice"]
    assert "免责D" in sec["disclaimer"]


def test_l1_blocked_without_llm() -> None:
    result = generate_opinion(
        fact_summary="我杀人了该怎么办",
        scene="其他综合",
        question="刑事辩护",
    )
    assert result.blocked is True
    assert result.risk_level == "L1"
    assert "拦截" in result.markdown or "不提供" in result.markdown


def test_opinion_api_mocked(client: TestClient) -> None:
    fake_md = """## 案情梳理
公司拖欠工资两个月。

## 法律分析
依据劳动合同法应及时足额支付 [1]。

## 行动建议
1. 书面催告
2. 申请劳动仲裁

## 免责声明
AI 草稿须律师审核。
"""
    hits = [
        {
            "id": "d1#0",
            "doc_id": "d1",
            "title": "中华人民共和国劳动合同法",
            "category": "法律",
            "article": "第三十条",
            "page": 1,
            "text": "用人单位应当及时足额支付劳动报酬。",
            "score": 0.9,
            "match": "vector",
            "effective_status": "现行有效",
            "effective_detail": "",
        }
    ]
    store = MagicMock()
    store.search.return_value = hits
    with patch("app.services.opinion.get_store", return_value=store):
        with patch("app.services.opinion.chat", return_value=fake_md):
            with patch("app.services.opinion.verify_answer") as ver:
                ver.return_value = MagicMock(answer=fake_md, sources=hits)
                resp = client.post(
                    "/api/opinions/generate",
                    json={
                        "fact_summary": "公司拖欠工资两个月，已签劳动合同。",
                        "scene": "劳动用工",
                        "question": "如何维权",
                    },
                )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["blocked"] is False
    assert "案情梳理" in body["markdown"] or body["sections"].get("case_summary")
    assert body["watermark"]
    assert "律师审核" in body["watermark"]
    assert body["risk_level"] in {"L2", "L3"}
