"""个人工作记录：分页 / 搜索 / 清空。"""
from __future__ import annotations

import pytest

from app.repositories import database as db
from app.services import user_records as records


@pytest.fixture()
def uid() -> int:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")
    row = db.query_one("SELECT id FROM users WHERE username = ?", ("rec_user",))
    if row:
        uid = int(row["id"])
    else:
        cur = db.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            ("rec_user", "x", "y", "user"),
        )
        uid = int(cur.lastrowid)
    db.execute("DELETE FROM user_records WHERE user_id = ?", (uid,))
    return uid


def test_list_records_pagination_and_search(uid: int) -> None:
    for i in range(15):
        records.save_record(
            uid,
            "calculator",
            f"诉讼费-{i}",
            f"合计 {i}.0",
            {"total": i},
        )
    records.save_record(uid, "calculator", "利息/逾期", "合计 99", {"total": 99})

    page1 = records.list_records(uid, "calculator", page=1, page_size=8)
    assert page1["total"] == 16
    assert len(page1["items"]) == 8
    assert page1["page_count"] == 2

    page2 = records.list_records(uid, "calculator", page=2, page_size=8)
    assert len(page2["items"]) == 8

    hit = records.list_records(uid, "calculator", page=1, page_size=10, q="利息")
    assert hit["total"] == 1
    assert hit["items"][0]["title"] == "利息/逾期"

    deleted = records.delete_records_by_kind(uid, "calculator")
    assert deleted == 16
    empty = records.list_records(uid, "calculator", page=1, page_size=8)
    assert empty["total"] == 0


def test_opinion_kind_save_and_list(uid: int) -> None:
    rid = records.save_record(
        uid,
        "opinion",
        "劳动用工意见书",
        "lawyer · 风险 L3",
        {"markdown": "## 案情", "mode": "lawyer"},
    )
    assert rid is not None
    listed = records.list_records(uid, "opinion", page=1, page_size=8)
    assert listed["total"] == 1
    assert listed["items"][0]["title"] == "劳动用工意见书"
    detail = records.get_record(uid, int(rid))
    assert detail and detail["payload"]["mode"] == "lawyer"
