# -*- coding: utf-8 -*-
"""清理自动化测试遗留的测试用户（保留 admin 与真实用户）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402

TEST_PREFIXES = (
    "testuser_", "iso_user_", "iso_", "tuser_", "api_empty_", "isoa_", "isob_",
    "api_empty_test", "demo_user", "other_user",
)

rows = db.query("SELECT id, username FROM users ORDER BY id")
removed = 0
for r in rows:
    name = r["username"]
    if name == "admin":
        continue
    if any(name.startswith(p) for p in TEST_PREFIXES) or name in ("demo_user", "other_user"):
        db.execute("DELETE FROM users WHERE id = ?", (r["id"],))
        db.execute("DELETE FROM tokens WHERE user_id = ?", (r["id"],))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (r["id"],))
        removed += 1
        print(f"已删除: {name} (id={r['id']})")

print(f"\n共清理 {removed} 个测试用户")
rows = db.query("SELECT id, username, role FROM users ORDER BY id")
print("剩余用户:")
for r in rows:
    print(f"  id={r['id']} user={r['username']} role={r['role']}")
