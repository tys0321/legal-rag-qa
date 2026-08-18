"""统一日志配置。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO, log_dir: Path | None = None) -> None:
    """配置根日志：控制台 + 可选文件输出。"""
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler（避免重复添加）
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        root.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
            file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
            file_handler.setFormatter(fmt)
            root.addHandler(file_handler)
