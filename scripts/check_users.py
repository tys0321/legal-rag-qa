# -*- coding: utf-8 -*-
"""检查当前用户表状态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402

db.init_db()
rows = db.query("SELECT id, username, created_at FROM users ORDER BY id")
print("用户数:", len(rows))
for r in rows:
    print(f"  id={r['id']} user={r['username']} created={r['created_at']}")

cols = db.query("PRAGMA table_info(users)")
print("users 列:", [c["name"] for c in cols])
