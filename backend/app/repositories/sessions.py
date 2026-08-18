"""会话仓储：多轮对话记忆（SQLite 持久化，按用户隔离）。"""
from __future__ import annotations

import uuid

from app.repositories import database as db


def _title_from(content: str, max_len: int = 24) -> str:
    """从首条用户消息生成会话标题。"""
    title = content.strip().replace("\n", " ")
    return title[:max_len] + ("…" if len(title) > max_len else "")


class SessionStore:
    """用户会话：创建/读取/追加/列出/删除/改名。"""

    def create(self, user_id: int, first_message: str = "") -> str:
        sid = uuid.uuid4().hex[:12]
        title = _title_from(first_message) if first_message else "新对话"
        db.execute(
            "INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)",
            (sid, user_id, title),
        )
        return sid

    def get(self, sid: str, user_id: int | None = None) -> dict | None:
        if user_id is not None:
            row = db.query_one(
                "SELECT * FROM sessions WHERE id = ? AND user_id = ?", (sid, user_id)
            )
        else:
            row = db.query_one("SELECT * FROM sessions WHERE id = ?", (sid,))
        return dict(row) if row else None

    def list_sessions(self, user_id: int) -> list[dict]:
        rows = db.query(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS msg_count
            FROM sessions s
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in rows]

    def messages(self, sid: str, user_id: int | None = None) -> list[dict]:
        """读取会话消息（校验归属）。"""
        sess = self.get(sid, user_id)
        if not sess:
            return []
        rows = db.query(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (sid,),
        )
        return [dict(r) for r in rows]

    def append(self, sid: str, role: str, content: str, user_id: int | None = None) -> None:
        """写入一条消息并更新会话时间。"""
        sess = self.get(sid, user_id)
        if not sess:
            return
        db.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (sid, role, content),
        )
        db.execute("UPDATE sessions SET updated_at = datetime('now','localtime') WHERE id = ?", (sid,))

    def rename(self, sid: str, title: str, user_id: int) -> bool:
        row = self.get(sid, user_id)
        if not row:
            return False
        db.execute("UPDATE sessions SET title = ? WHERE id = ?", (title.strip() or "新对话", sid))
        return True

    def delete(self, sid: str, user_id: int) -> bool:
        row = self.get(sid, user_id)
        if not row:
            return False
        db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        return True

    def delete_many(self, session_ids: list[str], user_id: int) -> int:
        """批量删除会话（只删属于该用户的），返回实际删除数量。"""
        if not session_ids:
            return 0
        removed = 0
        for sid in session_ids:
            row = db.query_one(
                "SELECT id FROM sessions WHERE id = ? AND user_id = ?", (sid, user_id)
            )
            if row:
                db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
                removed += 1
        return removed

    def clear_all(self, user_id: int) -> int:
        rows = db.query("SELECT id FROM sessions WHERE user_id = ?", (user_id,))
        for r in rows:
            db.execute("DELETE FROM sessions WHERE id = ?", (r["id"],))
        return len(rows)


def get_session_store() -> SessionStore:
    return SessionStore()
