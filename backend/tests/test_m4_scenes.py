"""M4.3：52 场景分类占位目录。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.services import scenes_catalog as catalog_svc
from app.services.slots import detect_scene


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


def test_catalog_has_52_and_7_mvp() -> None:
    catalog_svc.reload_catalog()
    data = catalog_svc.catalog_summary()
    assert data["total"] == 52
    assert data["active_count"] == 7
    assert data["coming_soon_count"] == 45
    assert len(data["mvp_ids"]) == 7
    assert "劳动用工" in data["mvp_ids"]
    ids = [x["id"] for x in data["items"]]
    assert len(ids) == len(set(ids))


def test_scenes_api(client: TestClient) -> None:
    resp = client.get("/api/scenes")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 52
    assert body["active_count"] == 7
    coming = [x for x in body["items"] if x["status"] == "coming_soon"]
    assert len(coming) == 45
    assert all(x["name"] for x in body["items"])


def test_scenes_api_filter_active(client: TestClient) -> None:
    resp = client.get("/api/scenes", params={"status": "active"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 7
    assert all(x["status"] == "active" for x in body["items"])


def test_detect_scene_still_mvp() -> None:
    catalog_svc.reload_catalog()
    assert detect_scene("公司拖欠工资还不给加班费") == "劳动用工"
