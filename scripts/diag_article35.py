# -*- coding: utf-8 -*-
"""诊断：宪法第三十五条是否在向量库中。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from vectorstore import get_store  # noqa: E402

store = get_store()
store.load()

hits = store.search("宪法第三十五条 公民权利", top_k=8, min_score=0.0)
print("=== 检索「宪法第三十五条 公民权利」top8 ===")
for h in hits:
    print(f"  {h['score']} | {h['title']} | {h['article']} | {h['text'][:50]!r}")

print("\n=== 库中含「第三十五条」的块 ===")
found = [m for m in store._metas if "第三十五条" in m.get("text", "")]
print("数量:", len(found))
for m in found[:5]:
    print(f"  - {m['title']} [{m['article']}] | {m['text'][:60]!r}")

print("\n=== 宪法2018修正文本 全部块号 ===")
arts = [m["article"] for m in store._metas if "2018年修正文本" in m["title"]]
print("条款列表:", arts[:80])
