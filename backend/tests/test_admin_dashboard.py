"""管理后台数据看板与批量审核。"""
from __future__ import annotations

from app.services.admin_dashboard import _day_keys, _fill_series, build_dashboard


def test_day_keys_length() -> None:
    keys = _day_keys(14)
    assert len(keys) == 14
    assert keys[0] < keys[-1]


def test_fill_series_pads_zeros() -> None:
    keys = ["2026-01-01", "2026-01-02", "2026-01-03"]
    rows = [{"d": "2026-01-02", "c": 5}]
    series = _fill_series(keys, rows)
    assert series == [
        {"date": "2026-01-01", "count": 0},
        {"date": "2026-01-02", "count": 5},
        {"date": "2026-01-03", "count": 0},
    ]


def test_build_dashboard_shape() -> None:
    data = build_dashboard(days=7)
    assert "summary" in data
    assert len(data["daily_messages"]) == 7
    assert len(data["daily_sessions"]) == 7
    assert len(data["daily_new_users"]) == 7
    assert isinstance(data["kb_categories"], list)
    assert isinstance(data["roles"], list)
    s = data["summary"]
    assert "user_count" in s
    assert "lawyer_pending" in s
