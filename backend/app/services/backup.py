"""版本快照服务：创建/列出/恢复/删除系统快照（无需 git）。

快照内容（zip 打包，带时间戳存 data/backups/）：
- mysql_dump.json → 用户/会话/消息等业务表（MySQL）
- vectorstore/    → 知识库向量索引（meta.jsonl + vectors.npy）
- uploads/        → 用户上传的文档

恢复流程：解压 → 恢复 MySQL 表 + 覆盖向量/上传目录 → 重置进程内向量库缓存。
"""
from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings
from app.repositories import database as db

logger = logging.getLogger("service.backup")

BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
SNAPSHOT_DIRS = ["vectorstore", "uploads"]
MYSQL_DUMP_NAME = "mysql_dump.json"


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_snapshot(description: str = "") -> dict:
    """创建快照。返回 {name, path, size, created_at, description}。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = PROJECT_ROOT / "data"

    from app.repositories.vector_store import get_store

    get_store().save()

    name = f"snapshot_{_now()}"
    if description:
        safe = "".join(c for c in description if c.isalnum() or c in " -_")
        name = f"{name}_{safe[:30]}"

    zip_path = BACKUP_DIR / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        dump = db.dump_tables()
        zf.writestr(
            MYSQL_DUMP_NAME,
            json.dumps(dump, ensure_ascii=False, indent=2),
        )
        for item in SNAPSHOT_DIRS:
            src = data_dir / item
            if src.is_dir():
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        zf.write(f, arcname=f"{item}/{f.relative_to(src).as_posix()}")
        zf.writestr(
            "snapshot.json",
            json.dumps(
                {
                    "name": name,
                    "description": description,
                    "created_at": _now(),
                    "engine": "mysql",
                },
                ensure_ascii=False,
            ),
        )

    size_mb = round(zip_path.stat().st_size / (1024 * 1024), 2)
    logger.info("创建快照 %s (%.2f MB)", name, size_mb)
    return {
        "name": name,
        "path": str(zip_path),
        "size_mb": size_mb,
        "created_at": _now(),
        "description": description,
    }


def list_snapshots() -> list[dict]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for zip_path in sorted(BACKUP_DIR.glob("snapshot_*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                info = json.loads(zf.read("snapshot.json").decode("utf-8"))
        except Exception:  # noqa: BLE001
            info = {"name": zip_path.stem, "description": "", "created_at": ""}
        snapshots.append(
            {
                "name": zip_path.stem,
                "description": info.get("description", ""),
                "created_at": info.get("created_at", ""),
                "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
            }
        )
    return snapshots


def delete_snapshot(name: str) -> bool:
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    zip_path = BACKUP_DIR / f"{safe}.zip"
    if zip_path.exists():
        zip_path.unlink()
        logger.info("删除快照 %s", name)
        return True
    return False


def restore_snapshot(name: str) -> dict:
    """恢复快照：解压文件 + 恢复 MySQL → 重置向量缓存。"""
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    zip_path = BACKUP_DIR / f"{safe}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"快照不存在: {name}")

    data_dir = PROJECT_ROOT / "data"
    restored = []
    mysql_payload: dict | None = None

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member in ("snapshot.json",) or member.endswith("/"):
                continue
            if member == MYSQL_DUMP_NAME or member == "app.db":
                # 旧版 app.db 快照不再直接恢复；仅处理 mysql_dump.json
                if member == MYSQL_DUMP_NAME:
                    mysql_payload = json.loads(zf.read(member).decode("utf-8"))
                    restored.append(member)
                continue
            clean = Path(member)
            if clean.is_absolute() or ".." in clean.parts:
                raise ValueError(f"快照含非法路径: {member}")
            dest = data_dir / clean
            if not str(dest.resolve()).startswith(str(data_dir.resolve())):
                raise ValueError(f"快照路径越界: {member}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            restored.append(member)

    if mysql_payload is not None:
        db.restore_tables(mysql_payload)

    from app.repositories import vector_store as vs

    vs._store = None  # type: ignore[attr-defined]

    logger.info("恢复快照 %s：%d 个条目", name, len(restored))
    return {"ok": True, "name": name, "restored_files": restored, "count": len(restored)}
