"""用户仓储：注册、登录、Token 管理（PBKDF2 密码哈希）。

注册约束：
- 用户名不可为空（去除首尾空格后至少 2 个字符）
- 密码必须同时包含字母和数字（且至少 6 位）
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from app.repositories import database as db

_ITERATIONS = 100_000

# 密码规则：至少 6 位，且必须同时含字母和数字
PASSWORD_MIN_LEN = 6
USERNAME_MIN_LEN = 2

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


class UserError(Exception):
    """注册/登录参数不合法。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_username(username: str) -> str:
    """校验并规范化用户名：非空、去空格后长度>=2。"""
    name = (username or "").strip()
    if not name:
        raise UserError("用户名不能为空")
    if len(name) < USERNAME_MIN_LEN:
        raise UserError(f"用户名至少 {USERNAME_MIN_LEN} 个字符")
    return name


def validate_password(password: str) -> str:
    """校验密码：至少 6 位，且必须同时包含字母和数字。"""
    if not password:
        raise UserError("密码不能为空")
    if len(password) < PASSWORD_MIN_LEN:
        raise UserError(f"密码至少 {PASSWORD_MIN_LEN} 位")
    if not _HAS_LETTER.search(password):
        raise UserError("密码必须包含字母")
    if not _HAS_DIGIT.search(password):
        raise UserError("密码必须包含数字")
    return password


def _hash_password(password: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256 哈希密码。"""
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return dk.hex()


def create_user(username: str, password: str, role: str = "user") -> dict | None:
    """注册用户（校验通过后创建）。用户名已存在返回 None。"""
    name = validate_username(username)
    validate_password(password)
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (name, pwd_hash, salt, role),
        )
    except db.sqlite3.IntegrityError:
        return None
    user = db.query_one("SELECT * FROM users WHERE username = ?", (name,))
    return dict(user) if user else None


def get_user_by_username(username: str) -> dict | None:
    user = db.query_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
    return dict(user) if user else None


def set_role(username: str, role: str) -> bool:
    """设置用户角色（admin / user）。返回是否成功。"""
    if role not in ("admin", "user"):
        return False
    cur = db.execute("UPDATE users SET role = ? WHERE username = ?", (role, username.strip()))
    return cur.rowcount > 0


def verify_password(user: dict, password: str) -> bool:
    expected = _hash_password(password, user["salt"])
    return hmac.compare_digest(expected, user["password_hash"])


def issue_token(user_id: int) -> str:
    """为用户签发随机 Token（64 hex）。"""
    token = secrets.token_hex(32)
    db.execute("INSERT INTO tokens (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def get_user_by_token(token: str) -> dict | None:
    row = db.query_one(
        """
        SELECT u.* FROM users u
        JOIN tokens t ON t.user_id = u.id
        WHERE t.token = ?
        """,
        (token,),
    )
    return dict(row) if row else None


def revoke_token(token: str) -> None:
    db.execute("DELETE FROM tokens WHERE token = ?", (token,))
