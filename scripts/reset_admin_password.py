# -*- coding: utf-8 -*-
"""将 admin 账号密码重置为 admin123（用户明确要求 admin/admin123），保留角色。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import users as user_repo  # noqa: E402
from app.repositories import database as db  # noqa: E402

admin = user_repo.get_user_by_username("admin")
if not admin:
    print("错误：admin 账号不存在！")
    sys.exit(1)

# 重置密码
import hashlib
import secrets

salt = secrets.token_hex(16)
pwd_hash = hashlib.pbkdf2_hmac(
    "sha256", "admin123".encode("utf-8"), salt.encode("utf-8"), 100_000
).hex()
db.execute(
    "UPDATE users SET password_hash = ?, salt = ?, role = 'admin' WHERE username = 'admin'",
    (pwd_hash, salt),
)

# 验证
again = user_repo.get_user_by_username("admin")
print(f"admin id={again['id']} role={again['role']}")
print("verify admin123:", user_repo.verify_password(again, "admin123"))
