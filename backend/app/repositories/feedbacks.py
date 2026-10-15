"""消息反馈仓储：有用 / 无用。"""
from __future__ import annotations

from app.core.errors import AppError
from app.repositories import database as db


def get_message_owner(message_id: int) -> dict | None:
    row = db.query_one(
        """
        SELECT m.id AS message_id, m.session_id, m.role, s.user_id
        FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.id = ?
        """,
        (message_id,),
    )
    return dict(row) if row else None


def upsert_feedback(
    *,
    message_id: int,
    user_id: int,
    rating: str,
    comment: str = "",
) -> dict:
    rating = (rating or "").strip().lower()
    if rating not in {"useful", "useless"}:
        raise AppError("rating 须为 useful 或 useless", 400)
    owner = get_message_owner(message_id)
    if not owner:
        raise AppError("消息不存在", 404)
    if int(owner["user_id"]) != int(user_id):
        raise AppError("无权反馈该消息", 403)
    if owner.get("role") != "assistant":
        raise AppError("只能对助手回复反馈", 400)

    existing = db.query_one(
        "SELECT id FROM message_feedbacks WHERE message_id = ? AND user_id = ?",
        (message_id, user_id),
    )
    if existing:
        db.execute(
            "UPDATE message_feedbacks SET rating = ?, comment = ? WHERE id = ?",
            (rating, (comment or "")[:500], existing["id"]),
        )
        fid = int(existing["id"])
    else:
        cur = db.execute(
            """
            INSERT INTO message_feedbacks (message_id, user_id, rating, comment)
            VALUES (?, ?, ?, ?)
            """,
            (message_id, user_id, rating, (comment or "")[:500]),
        )
        fid = int(cur.lastrowid)

    row = db.query_one("SELECT * FROM message_feedbacks WHERE id = ?", (fid,))
    return dict(row) if row else {"id": fid, "message_id": message_id, "rating": rating}


def list_feedbacks(*, limit: int = 100, rating: str | None = None) -> list[dict]:
    limit = max(1, min(int(limit or 100), 500))
    if rating:
        rows = db.query(
            """
            SELECT f.id, f.message_id, f.user_id, u.username, f.rating, f.comment,
                   f.created_at, LEFT(m.content, 160) AS message_preview, s.id AS session_id
            FROM message_feedbacks f
            JOIN users u ON u.id = f.user_id
            JOIN messages m ON m.id = f.message_id
            JOIN sessions s ON s.id = m.session_id
            WHERE f.rating = ?
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (rating, limit),
        )
    else:
        rows = db.query(
            """
            SELECT f.id, f.message_id, f.user_id, u.username, f.rating, f.comment,
                   f.created_at, LEFT(m.content, 160) AS message_preview, s.id AS session_id
            FROM message_feedbacks f
            JOIN users u ON u.id = f.user_id
            JOIN messages m ON m.id = f.message_id
            JOIN sessions s ON s.id = m.session_id
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
    return [dict(r) for r in rows]


def feedback_stats() -> dict:
    rows = db.query(
        "SELECT rating, COUNT(*) AS c FROM message_feedbacks GROUP BY rating"
    )
    useful = 0
    useless = 0
    for r in rows:
        if r["rating"] == "useful":
            useful = int(r["c"])
        elif r["rating"] == "useless":
            useless = int(r["c"])
    return {"useful": useful, "useless": useless, "total": useful + useless}
