"""确保仅 tys 为管理员。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.repositories import database as db  # noqa: E402
from app.repositories import users as user_repo  # noqa: E402


def main() -> None:
    db.init_db()
    sole = settings.sole_admin_username
    u = user_repo.get_user_by_username(sole)
    if not u:
        raise SystemExit(f"账号不存在: {sole}")
    db.execute("UPDATE users SET role = 'admin' WHERE username = ?", (sole,))
    cur = db.execute(
        "UPDATE users SET role = 'user' WHERE role = 'admin' AND username <> ?",
        (sole,),
    )
    print(f"sole_admin={sole} demoted_others={cur.rowcount}")
    rows = db.query("SELECT id, username, role FROM users WHERE role = 'admin'")
    print("admins=", [dict(r) for r in rows])


if __name__ == "__main__":
    main()
