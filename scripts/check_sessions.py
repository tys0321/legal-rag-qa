# -*- coding: utf-8 -*-
"""检查会话数据与用户归属。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402

rows = db.query(
    "SELECT s.id, s.user_id, s.title, u.username FROM sessions s "
    "JOIN users u ON u.id = s.user_id ORDER BY s.id"
)
print("会话数:", len(rows))
for r in rows:
    print(f"  session={r['id']} user_id={r['user_id']} user={r['username']} title={r['title']}")

users = db.query("SELECT id, username FROM users ORDER BY id")
print("\n用户:", [(r["id"], r["username"]) for r in users])
