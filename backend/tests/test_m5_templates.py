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


def test_catalog_has_templates() -> None:
    data = tpl.list_templates()
    assert data["total"] >= 8
    ids = {x["id"] for x in data["items"]}
    assert "civil_complaint" in ids
    assert "power_of_attorney" in ids
    assert "judgment_outline" in ids
    assert "indictment_outline" in ids
    assert "人工审核" in data["watermark"] or "律师审核" in data["watermark"]
    assert tpl.list_templates(audience="judge")["total"] >= 2
    assert tpl.list_templates(audience="prosecutor")["total"] >= 2


def test_fill_civil_complaint() -> None:
    tpl.reload_catalog()
    result = tpl.fill_template(
        "civil_complaint",
        {
            "court": "示例区人民法院",
            "plaintiff_name": "张三",
            "plaintiff_gender": "男",
            "plaintiff_birth": "1990年1月1日",
            "plaintiff_nation": "汉族",
            "plaintiff_job": "职员",
            "plaintiff_address": "某市某区某路1号",
            "plaintiff_phone": "13800138000",
            "defendant_name": "李四",
            "defendant_address": "某市某街2号",
            "claims": "一、判令被告支付货款 10000 元；\n二、本案诉讼费用由被告负担。",
            "facts": "双方于2025年签订买卖合同后被告未按约定付款。",
            "evidence": "1.买卖合同；2.转账凭证。",
            "copies": "1",
            "date": "2026年10月15日",
        },
    )
    assert result["missing_required"] == []
    assert "民事起诉状" in result["markdown"]
    assert "张三" in result["markdown"]
    assert "诉讼请求" in result["markdown"]
    assert "事实和理由" in result["markdown"]
    assert "AI 生成草稿" in result["markdown"]
    assert "示例区人民法院" in result["markdown"]
    assert "本起诉状副本" in result["markdown"]


def test_fill_rejects_bad_phone() -> None:
    tpl.reload_catalog()
    with pytest.raises(Exception) as ei:
        tpl.fill_template(
            "civil_complaint",
            {
                "court": "示例区人民法院",
                "plaintiff_name": "张三",
                "plaintiff_address": "某市某区某路1号",
                "plaintiff_phone": "12345",
                "defendant_name": "李四",
                "defendant_address": "某市某街2号",
                "claims": "一、判令被告支付货款 10000 元",
                "facts": "双方签订买卖合同后被告未付款。",
            },
        )
    assert "手机号" in str(ei.value)


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
    assert body["total"] >= 8

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
                "matter": "拖欠服务费",
                "facts": "对方拖欠服务费未付。",
                "legal_basis": "依据合同法相关规定，债务人应当按约履行付款义务。",
                "demands": "请于收到本函后 7 日内支付。",
                "law_firm": "某某律师事务所",
                "lawyer_name": "张律师",
            }
        },
    )
    assert filled.status_code == 200, filled.text
    out = filled.json()
    assert out["id"] == tid
    assert "律师函" in out["markdown"]
    assert out["watermark"]
    assert "审核" in out["watermark"]
