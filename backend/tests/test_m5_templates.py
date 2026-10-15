"""M5.2：文书模板 ×8。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.services import templates as tpl


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


def test_catalog_has_eight() -> None:
    data = tpl.list_templates()
    assert data["total"] == 8
    ids = {x["id"] for x in data["items"]}
    assert "civil_complaint" in ids
    assert "power_of_attorney" in ids
    assert "律师审核" in data["watermark"]


def test_fill_civil_complaint() -> None:
    result = tpl.fill_template(
        "civil_complaint",
        {
            "court": "示例区人民法院",
            "plaintiff_name": "张三",
            "plaintiff_address": "某市某区",
            "defendant_name": "李四",
            "defendant_address": "某市某街",
            "claims": "1. 判令被告支付货款 10000 元",
            "facts": "双方签订买卖合同后被告未付款。",
            "date": "2026年10月15日",
        },
    )
    assert result["missing_required"] == []
    assert "民事起诉状" in result["markdown"]
    assert "张三" in result["markdown"]
    assert "AI 生成草稿" in result["markdown"]
    assert "示例区人民法院" in result["markdown"]
    # 未填选填项保留占位
    assert "【待填写】" in result["markdown"]


def test_fill_marks_missing_and_placeholder() -> None:
    result = tpl.fill_template("labor_arbitration", {"applicant_name": "王五"})
    assert "applicant_name" not in result["missing_required"]
    assert "commission" in result["missing_required"]
    assert "王五" in result["markdown"]
    assert "【待填写】" in result["markdown"]


def test_unknown_template_404(client: TestClient) -> None:
    resp = client.get("/api/templates/not_exist")
    assert resp.status_code == 404


def test_templates_api(client: TestClient) -> None:
    lst = client.get("/api/templates")
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body["total"] == 8

    tid = "lawyer_letter"
    detail = client.get(f"/api/templates/{tid}")
    assert detail.status_code == 200
    assert len(detail.json()["fields"]) >= 3

    filled = client.post(
        f"/api/templates/{tid}",
        json={
            "fields": {
                "addressee": "某某公司",
                "client_name": "赵六",
                "facts": "对方拖欠服务费未付。",
                "demands": "请于收到本函后 7 日内支付。",
                "law_firm": "待定",
                "lawyer_name": "待定",
            }
        },
    )
    assert filled.status_code == 200, filled.text
    out = filled.json()
    assert out["id"] == tid
    assert "律师函" in out["markdown"]
    assert out["watermark"]
    assert "须律师审核" in out["watermark"]
