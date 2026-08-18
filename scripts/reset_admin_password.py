# -*- coding: utf-8 -*-
"""重置 admin 账号密码（从环境变量或命令行参数读取，不硬编码），保留角色。

用法：
  python reset_admin_password.py              # 从 ADMIN_PASSWORD 环境变量读取
  python reset_admin_password.py "新密码"     # 或直接传入命令行参数
"""
import getpass
import hashlib
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import users as user_repo  # noqa: E402
from app.repositories import database as db  # noqa: E402

admin = user_repo.get_user_by_username("admin")
if not admin:
    print("错误：admin 账号不存在！")
    sys.exit(1)

# 优先级：命令行参数 > 环境变量 ADMIN_PASSWORD > 交互输入
password = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ADMIN_PASSWORD", "")
if not password:
    password = getpass.getpass("请输入新的 admin 密码（至少 6 位，含字母和数字）: ")

# 复用注册校验
try:
    user_repo.validate_password(password)
except user_repo.UserError as exc:
    print(f"密码不合法：{exc.message}")
    sys.exit(1)

# 重置密码
salt = secrets.token_hex(16)
pwd_hash = hashlib.pbkdf2_hmac(
    "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
).hex()
db.execute(
    "UPDATE users SET password_hash = ?, salt = ?, role = 'admin' WHERE username = 'admin'",
    (pwd_hash, salt),
)

# 验证
again = user_repo.get_user_by_username("admin")
print(f"admin id={again['id']} role={again['role']}")
print("密码重置成功（密码内容不显示）")
