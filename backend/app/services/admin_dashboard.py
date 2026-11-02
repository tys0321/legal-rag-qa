"""管理后台数据看板：汇总指标 + 近 N 日趋势 + 知识库分类。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.repositories import database as db
from app.repositories import feedbacks as feedback_repo
from app.repositories.vector_store import get_store


def _day_keys(days: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _fill_series(keys: list[str], rows: list[dict], date_key: str = "d", count_key: str = "c") -> list[dict]:
    by_day: dict[str, int] = {}
    for r in rows:
        raw = r.get(date_key)
        if raw is None:
            continue
        if isinstance(raw, datetime):
            k = raw.date().isoformat()
        elif isinstance(raw, date):
            k = raw.isoformat()
        else:
            k = str(raw)[:10]
        by_day[k] = int(r.get(count_key) or 0)
    return [{"date": k, "count": by_day.get(k, 0)} for k in keys]


def _count_lawyers() -> tuple[int, int]:
    rows = db.query(
        "SELECT status, COUNT(*) AS c FROM lawyer_profiles GROUP BY status"
    )
    pending = 0
    approved = 0
    for r in rows:
        st = (r.get("status") or "").lower()
        c = int(r.get("c") or 0)
        if st == "pending":
            pending = c
        elif st == "approved":
            approved = c
    return pending, approved


def _role_counts() -> list[dict]:
    rows = db.query("SELECT role, COUNT(*) AS c FROM users GROUP BY role")
    out = []
    for r in rows:
        out.append({"role": str(r.get("role") or "user"), "count": int(r.get("c") or 0)})
    return sorted(out, key=lambda x: x["role"])


def _kb_categories() -> list[dict]:
    kb = get_store().stats()
    docs: dict[str, Any] = kb.get("docs") or {}
    cats: dict[str, dict[str, int]] = {}
    for meta in docs.values():
        name = (meta.get("category") or "未分类").strip() or "未分类"
        bucket = cats.setdefault(name, {"docs": 0, "chunks": 0})
        bucket["docs"] += 1
        bucket["chunks"] += int(meta.get("chunks") or 0)
    items = [
        {"name": k, "docs": v["docs"], "chunks": v["chunks"]}
        for k, v in cats.items()
    ]
    items.sort(key=lambda x: (-x["chunks"], x["name"]))
    return items


def build_dashboard(days: int = 14) -> dict:
    days = max(7, min(int(days), 30))
    keys = _day_keys(days)
    start = keys[0]

    users = db.query_one("SELECT COUNT(*) AS c FROM users") or {"c": 0}
    sessions = db.query_one("SELECT COUNT(*) AS c FROM sessions") or {"c": 0}
    messages = db.query_one("SELECT COUNT(*) AS c FROM messages") or {"c": 0}
    kb = get_store().stats()
    fb = feedback_repo.feedback_stats()
    pending, approved = _count_lawyers()

    user_count = int(users["c"])
    session_count = int(sessions["c"])
    message_count = int(messages["c"])
    fb_total = int(fb.get("total") or 0)
    fb_useful = int(fb.get("useful") or 0)
    fb_useless = int(fb.get("useless") or 0)
    useful_rate = round(fb_useful / fb_total * 100, 1) if fb_total else None
    avg_msg = round(message_count / session_count, 2) if session_count else 0.0

    msg_rows = db.query(
        """
        SELECT DATE(created_at) AS d, COUNT(*) AS c
        FROM messages
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY d
        """,
        (start,),
    )
    sess_rows = db.query(
        """
        SELECT DATE(created_at) AS d, COUNT(*) AS c
        FROM sessions
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY d
        """,
        (start,),
    )
    user_rows = db.query(
        """
        SELECT DATE(created_at) AS d, COUNT(*) AS c
        FROM users
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY d
        """,
        (start,),
    )

    return {
        "summary": {
            "user_count": user_count,
            "session_count": session_count,
            "message_count": message_count,
            "doc_count": int(kb.get("doc_count") or 0),
            "chunk_count": int(kb.get("chunk_count") or 0),
            "lawyer_pending": pending,
            "lawyer_approved": approved,
            "feedback_total": fb_total,
            "feedback_useful": fb_useful,
            "feedback_useless": fb_useless,
            "useful_rate": useful_rate,
            "avg_messages_per_session": avg_msg,
        },
        "roles": _role_counts(),
        "daily_messages": _fill_series(keys, msg_rows),
        "daily_sessions": _fill_series(keys, sess_rows),
        "daily_new_users": _fill_series(keys, user_rows),
        "kb_categories": _kb_categories(),
    }
