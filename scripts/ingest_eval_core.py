"""将 data/kb/eval_core 小批量入库（演示用核心法规）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# 无本地模型缓存时允许下载
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.pop("HF_HUB_OFFLINE", None)

from app.core.config import PROJECT_ROOT, settings  # noqa: E402
from app.services.ingest import ingest_documents  # noqa: E402
from app.repositories.vector_store import get_store  # noqa: E402


def main() -> None:
    kb = PROJECT_ROOT / "data" / "kb" / "eval_core"
    if not kb.exists():
        raise SystemExit(f"missing kb: {kb}")
    print("kb=", kb)
    print("vector_backend=", settings.vector_backend)
    result = ingest_documents(kb)
    print("ingest=", result)
    print("stats=", get_store().stats())


if __name__ == "__main__":
    main()
