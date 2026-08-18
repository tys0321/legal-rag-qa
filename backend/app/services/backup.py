"""版本快照服务：创建/列出/恢复/删除系统快照（无需 git）。

快照内容（zip 打包，带时间戳存 data/backups/）：
- app.db          → 用户/会话/消息数据
- vectorstore/    → 知识库向量索引（meta.jsonl + vectors.npy）
- uploads/        → 用户上传的文档

恢复流程：解压快照覆盖对应文件 → 重置向量库与数据库缓存（进程内生效，无需重启）。
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings

logger = logging.getLogger("service.backup")

# 快照目录
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

# 要打包的相对路径（相对 data/）
SNAPSHOT_ITEMS = ["app.db", "vectorstore", "uploads"]


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_snapshot(description: str = "") -> dict:
    """创建快照。返回 {name, path, size, created_at, description}。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = PROJECT_ROOT / "data"

    # 确保向量库已落盘
    from app.repositories.vector_store import get_store
    get_store().save()

    name = f"snapshot_{_now()}"
    if description:
        safe = "".join(c for c in description if c.isalnum() or c in " -_")
        name = f"{name}_{safe[:30]}"

    zip_path = BACKUP_DIR / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in SNAPSHOT_ITEMS:
            src = data_dir / item
            if src.is_file():
                zf.write(src, arcname=item)
            elif src.is_dir():
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        zf.write(f, arcname=f"{item}/{f.relative_to(src).as_posix()}")
        # 写入说明
        zf.writestr("snapshot.json", json.dumps({
            "name": name,
            "description": description,
            "created_at": _now(),
        }, ensure_ascii=False))

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
    """列出全部快照（按时间倒序）。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for zip_path in sorted(BACKUP_DIR.glob("snapshot_*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                info = json.loads(zf.read("snapshot.json").decode("utf-8"))
        except Exception:  # noqa: BLE001
            info = {"name": zip_path.stem, "description": "", "created_at": ""}
        snapshots.append({
            "name": zip_path.stem,
            "description": info.get("description", ""),
            "created_at": info.get("created_at", ""),
            "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
        })
    return snapshots


def delete_snapshot(name: str) -> bool:
    """删除快照。"""
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    zip_path = BACKUP_DIR / f"{safe}.zip"
    if zip_path.exists():
        zip_path.unlink()
        logger.info("删除快照 %s", name)
        return True
    return False


def restore_snapshot(name: str) -> dict:
    """恢复快照：解压覆盖 → 重置缓存。返回统计信息。"""
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    zip_path = BACKUP_DIR / f"{safe}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"快照不存在: {name}")

    data_dir = PROJECT_ROOT / "data"
    restored = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member == "snapshot.json" or member.endswith("/"):
                continue
            # 路径穿越防护：拒绝绝对路径与 .. 前缀
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

    # 重置进程内缓存：向量库单例 + 数据库连接
    from app.repositories import database as db
    from app.repositories import vector_store as vs

    vs._store = None
    db._lock.acquire()
    try:
        db.get_conn().close()
    finally:
        db._lock.release()

    logger.info("恢复快照 %s：%d 个文件", name, len(restored))
    return {"ok": True, "name": name, "restored_files": restored, "count": len(restored)}
