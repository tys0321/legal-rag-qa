# -*- coding: utf-8 -*-
"""一次性脚本：初始化数据库 schema（含 role 列），并将 admin 账号设为管理员。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402
from app.repositories import users as user_repo  # noqa: E402

# 1) 初始化 schema（自动补 role 列）
db.init_db()

# 2) 确认 admin 账号存在
admin = user_repo.get_user_by_username("admin")
if not admin:
    print("警告：admin 账号不存在，跳过设置。")
else:
    print(f"找到 admin 账号: id={admin['id']} 当前 role={admin.get('role', 'N/A')}")
    ok = user_repo.set_role("admin", "admin")
    print(f"设置管理员: {'成功' if ok else '失败'}")
    again = user_repo.get_user_by_username("admin")
    print(f"确认 role={again.get('role')}")

# 3) 打印所有用户
rows = db.query("SELECT id, username, role, created_at FROM users ORDER BY id")
print("\n当前用户列表:")
for r in rows:
    print(f"  id={r['id']} user={r['username']} role={r['role']} created={r['created_at']}")
