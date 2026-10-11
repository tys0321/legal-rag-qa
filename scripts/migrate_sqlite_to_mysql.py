"""一次性将旧版 data/app.db（SQLite）迁移到 MySQL。

用法（仓库根目录，已启动 MySQL 并配置 .env）：
  python scripts/migrate_sqlite_to_mysql.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.repositories import database as db  # noqa: E402

SQLITE_PATH = ROOT / "data" / "app.db"
TABLES = ["users", "tokens", "sessions", "messages", "admin_logs"]


def main() -> None:
    if not SQLITE_PATH.exists():
        print(f"未找到 {SQLITE_PATH}，无需迁移。")
        return

    db.init_db()
    src = sqlite3.connect(str(SQLITE_PATH))
    src.row_factory = sqlite3.Row

    payload: dict[str, list[dict]] = {}
    for t in TABLES:
        try:
            rows = src.execute(f"SELECT * FROM {t}").fetchall()
        except sqlite3.Error as exc:
            print(f"跳过表 {t}: {exc}")
            payload[t] = []
            continue
        payload[t] = [dict(r) for r in rows]
        print(f"读取 {t}: {len(payload[t])} 行")

    src.close()
    db.restore_tables(payload)
    print(
        f"已写入 MySQL {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    print("建议确认无误后自行备份并移除 data/app.db（可选）。")


if __name__ == "__main__":
    main()
