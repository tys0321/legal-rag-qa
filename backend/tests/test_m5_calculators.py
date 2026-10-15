"""M5.3：法律计算器 ×5。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.services import calculators as calc


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


def test_catalog_has_five() -> None:
    data = calc.list_calculators()
    assert data["total"] == 5
    assert "估算仅供参考" in data["notice"]
    ids = {x["id"] for x in data["items"]}
    assert ids == {
        "litigation_fee",
        "private_lend_interest",
        "work_injury",
        "traffic_medical",
        "overtime_pay",
    }


def test_litigation_fee_brackets() -> None:
    # ≤1万 → 50
    r = calc.run_calculator("litigation_fee", {"amount": 5000})
    assert r["total"] == 50.0
    # 10万：50 + 90000*0.025 = 50+2250=2300
    r2 = calc.run_calculator("litigation_fee", {"amount": 100000})
    assert r2["total"] == 2300.0
    r3 = calc.run_calculator("litigation_fee", {"amount": 100000, "half_fee": "是"})
    assert r3["total"] == 1150.0


def test_interest_cap() -> None:
    r = calc.run_calculator(
        "private_lend_interest",
        {"principal": 100000, "annual_rate": 0.5, "days": 365, "cap_by_lpr": "是"},
    )
    assert r["total"] > 0
    assert any("超过" in w for w in r["warnings"])
    # LPR 0.031 * 4 = 0.124 → 100000*0.124 = 12400
    assert abs(r["total"] - 12400.0) < 0.02


def test_work_injury_grade10() -> None:
    r = calc.run_calculator("work_injury", {"monthly_wage": 6000, "grade": 10, "avg_wage": 8000})
    # 7 个月
    assert r["total"] == 42000.0


def test_traffic_and_overtime() -> None:
    t = calc.run_calculator(
        "traffic_medical",
        {"hospital": 1000, "medicine": 200, "nursing": 100, "nutrition": 0, "transport": 50, "other": 0},
    )
    assert t["total"] == 1350.0
    assert "估算仅供参考" in t["notice"]

    o = calc.run_calculator(
        "overtime_pay",
        {
            "monthly_wage": 4350,  # 便于整除：4350/21.75/8 = 25
            "weekday_hours": 8,
            "restday_hours": 0,
            "holiday_hours": 0,
            "workdays_per_month": 21.75,
        },
    )
    # 25 * 1.5 * 8 = 300
    assert abs(o["total"] - 300.0) < 0.05


def test_api(client: TestClient) -> None:
    lst = client.get("/api/calculators")
    assert lst.status_code == 200
    assert lst.json()["total"] == 5

    detail = client.get("/api/calculators/litigation_fee")
    assert detail.status_code == 200
    assert len(detail.json()["fields"]) >= 1

    bad = client.post("/api/calculators/litigation_fee", json={"inputs": {}})
    assert bad.status_code == 400

    ok = client.post("/api/calculators/litigation_fee", json={"inputs": {"amount": 8000}})
    assert ok.status_code == 200
    body = ok.json()
    assert body["total"] == 50
    assert "估算仅供参考" in body["notice"]
