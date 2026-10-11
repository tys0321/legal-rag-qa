"""MySQL 数据库访问层：用户、会话、审计等业务数据。

任务书硬性要求使用 MySQL；通过 PyMySQL 提供与原先相近的 execute/query API。
占位符仍写 ``?``，层内自动转换为 ``%s``。
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from typing import Any

import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError  # 供上层 except db.IntegrityError

from app.core.config import settings

logger = logging.getLogger("db")

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    firm_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tokens (
    token VARCHAR(128) PRIMARY KEY,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(32) PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '新对话',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sessions_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(32) NOT NULL,
    role VARCHAR(32) NOT NULL,
    content MEDIUMTEXT NOT NULL,
    meta_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_messages_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    actor_id INT NULL,
    actor_name VARCHAR(64) NULL,
    action VARCHAR(64) NOT NULL,
    detail TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _adapt_sql(sql: str) -> str:
    """将 ``?`` 占位符转为 PyMySQL 的 ``%s``，并避开字面量百分号问题。"""
    return sql.replace("%", "%%").replace("?", "%s")


def _normalize_row(row: dict | None) -> dict | None:
    """将 datetime 转为字符串，保持与旧 SQLite TEXT 字段及 Pydantic str 模型兼容。"""
    if row is None:
        return None
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def get_conn() -> pymysql.Connection:
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def init_db() -> None:
    """建库（若不存在）并初始化表结构。"""
    # 尝试建库；Docker 已预创建库时普通用户可能无 CREATE 权限，忽略即可
    try:
        root_conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            with root_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            root_conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.info("跳过 CREATE DATABASE（可能已由 Compose 创建）: %s", exc)

    with _lock:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                for stmt in _SCHEMA.split(";"):
                    s = stmt.strip()
                    if s:
                        cur.execute(s)
                # 兼容旧库：补 firm_id / meta_json
                cur.execute("SHOW COLUMNS FROM users LIKE 'firm_id'")
                if not cur.fetchone():
                    cur.execute("ALTER TABLE users ADD COLUMN firm_id INT NULL")
                cur.execute("SHOW COLUMNS FROM messages LIKE 'meta_json'")
                if not cur.fetchone():
                    cur.execute("ALTER TABLE messages ADD COLUMN meta_json JSON NULL")
            conn.commit()
            logger.info(
                "MySQL 就绪: %s:%s/%s",
                settings.mysql_host,
                settings.mysql_port,
                settings.mysql_database,
            )
        finally:
            conn.close()


def execute(sql: str, params: tuple | list = ()) -> Any:
    with _lock:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(_adapt_sql(sql), params)
            conn.commit()
            return cur
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def query(sql: str, params: tuple | list = ()) -> list[dict]:
    with _lock:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(_adapt_sql(sql), params)
            rows = cur.fetchall()
            return [_normalize_row(r) for r in rows]  # type: ignore[misc]
        finally:
            conn.close()


def query_one(sql: str, params: tuple | list = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def ping() -> bool:
    """健康检查：能否执行 SELECT 1。"""
    try:
        row = query_one("SELECT 1 AS ok")
        return bool(row and row.get("ok") == 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MySQL ping 失败: %s", exc)
        return False


def dump_tables() -> dict[str, list[dict]]:
    """导出业务表为可 JSON 序列化结构（备份用）。"""
    tables = ["users", "tokens", "sessions", "messages", "admin_logs"]
    out: dict[str, list[dict]] = {}
    for t in tables:
        rows = query(f"SELECT * FROM {t}")
        # datetime 等转 str
        serializable = []
        for r in rows:
            item = {}
            for k, v in r.items():
                item[k] = v.isoformat(sep=" ") if hasattr(v, "isoformat") else v
            serializable.append(item)
        out[t] = serializable
    return out


def restore_tables(data: dict[str, list[dict]]) -> None:
    """从 dump_tables 结构恢复（先清空再插入，注意外键顺序）。"""
    order = ["admin_logs", "messages", "tokens", "sessions", "users"]
    insert_order = ["users", "sessions", "tokens", "messages", "admin_logs"]
    with _lock:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                for t in order:
                    cur.execute(f"DELETE FROM {t}")
                for t in insert_order:
                    rows = data.get(t) or []
                    if not rows:
                        continue
                    cols = list(rows[0].keys())
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_sql = ", ".join(f"`{c}`" for c in cols)
                    sql = f"INSERT INTO {t} ({col_sql}) VALUES ({placeholders})"
                    for r in rows:
                        cur.execute(sql, tuple(r.get(c) for c in cols))
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
