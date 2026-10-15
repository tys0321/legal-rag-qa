"""七场景评测：检索命中率（引用相关法是否出现在 top-k）。

用法（在仓库根目录）:
  python scripts/run_eval_citations.py
  python scripts/run_eval_citations.py --top-k 8 --out data/logs/eval_report.json

说明:
  - 默认只测混合/向量检索命中，不调用 LLM（成本低、可重复）。
  - 命中定义：任一 expected_laws 子串出现在命中文档 title 中。
  - 目标：overall hit_rate >= 0.90（与 PRD 引用准确率目标对齐的可自动指标）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.repositories.vector_store import get_store  # noqa: E402


def _hit(titles: list[str], expected: list[str]) -> bool:
    blob = " ".join(titles)
    return any(e and e in blob for e in expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--set",
        default=str(ROOT / "configs" / "eval_set_7scenes.json"),
        help="评测集路径",
    )
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "logs" / "eval_citation_report.json"),
    )
    args = parser.parse_args()

    data = json.loads(Path(args.set).read_text(encoding="utf-8"))
    items = data.get("items") or []
    target = float(data.get("target_citation_hit_rate") or 0.9)

    store = get_store()
    results = []
    by_scene: dict[str, list[bool]] = defaultdict(list)

    for it in items:
        q = it["question"]
        expected = list(it.get("expected_laws") or [])
        hits = store.search(q, top_k=args.top_k, min_score=0.0)
        titles = [str(h.get("title") or "") for h in hits]
        ok = _hit(titles, expected)
        by_scene[it.get("scene") or "未分类"].append(ok)
        results.append(
            {
                "id": it.get("id"),
                "scene": it.get("scene"),
                "question": q,
                "expected_laws": expected,
                "hit": ok,
                "top_titles": titles[:5],
            }
        )

    total = len(results)
    hits_n = sum(1 for r in results if r["hit"])
    rate = (hits_n / total) if total else 0.0
    scene_rates = {
        s: (sum(1 for x in xs if x) / len(xs) if xs else 0.0) for s, xs in by_scene.items()
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "retrieval_hit",
        "top_k": args.top_k,
        "total": total,
        "hits": hits_n,
        "hit_rate": round(rate, 4),
        "target": target,
        "pass": rate >= target,
        "scene_rates": {k: round(v, 4) for k, v in scene_rates.items()},
        "items": results,
        "note": "检索命中率是引用准确率的可自动化代理指标；端到端生成引用准确率需人工抽检或 --live（未实现）。",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"total={total} hits={hits_n} hit_rate={rate:.2%} target={target:.0%} pass={report['pass']}")
    for s, v in sorted(scene_rates.items()):
        print(f"  {s}: {v:.2%}")
    print(f"report -> {out}")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
