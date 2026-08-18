# -*- coding: utf-8 -*-
"""回填存量数据的法规时效状态（Phase 1 入库的数据没有 effective_status 字段）。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories.vector_store import get_store  # noqa: E402
from app.services.effective import detect_status  # noqa: E402

store = get_store()
store.load()

# 按文档分组，取每个文档的首块文本做检测
docs: dict[str, dict] = {}
for meta in store._metas:
    d = docs.setdefault(meta["doc_id"], {"title": meta["title"], "texts": []})
    d["texts"].append(meta.get("text", ""))

updated = 0
skipped = 0
for doc_id, info in docs.items():
    # 已有状态则跳过
    sample_meta = next((m for m in store._metas if m["doc_id"] == doc_id), None)
    if sample_meta and sample_meta.get("effective_status"):
        skipped += 1
        continue
    head = "\n".join(info["texts"][:6])
    body = "\n".join(info["texts"][:60])
    status = detect_status(info["title"], head, body)
    # 回写该文档所有块
    for meta in store._metas:
        if meta["doc_id"] == doc_id:
            meta["effective_status"] = status.status
            meta["effective_detail"] = status.detail
            meta["effective_evidence"] = status.evidence[:2]
    updated += 1

store.save()

counter = Counter(
    m.get("effective_status", "未知")
    for m in store._metas
    if m.get("effective_status")
)
print(f"回填完成：更新 {updated} 篇，跳过 {skipped} 篇")
print("状态分布:", dict(counter))
