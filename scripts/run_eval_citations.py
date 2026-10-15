"""七场景评测：期望法规是否可被命中。

默认 mode=lexical：扫描 data/kb/eval_core，不依赖嵌入/向量库。
可选 mode=retrieval：走向量库（需已入库）。

用法:
  python scripts/run_eval_citations.py
  python scripts/run_eval_citations.py --mode retrieval
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _hit(blob: str, expected: list[str]) -> bool:
    return any(e and e in blob for e in expected)


def _load_kb_docs(kb_dir: Path) -> list[dict]:
    docs = []
    for p in sorted(kb_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".md", ".txt", ".markdown"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        title = p.stem
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            title = m.group(1).strip()
        docs.append({"title": title, "text": text})
    return docs


def _ngrams(question: str) -> set[str]:
    """重叠 2~4 字片，避免整句被当成一个超长 token。"""
    chars = re.findall(r"[\u4e00-\u9fff]", question)
    toks: set[str] = set()
    for n in (2, 3, 4):
        for i in range(0, max(0, len(chars) - n + 1)):
            toks.add("".join(chars[i : i + n]))
    return toks


def _lexical_top(question: str, docs: list[dict], top_k: int) -> list[str]:
    toks = _ngrams(question)
    scored: list[tuple[int, str]] = []
    for d in docs:
        score = 0
        title = d["title"]
        text = d["text"]
        for tok in toks:
            if tok in title:
                score += 4
            elif tok in text:
                score += 1
        if score > 0:
            scored.append((score, title))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [t for _, t in scored[:top_k]]


def _retrieval_top(question: str, top_k: int) -> list[str]:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.repositories.vector_store import get_store

    store = get_store()
    if int(store.stats().get("chunk_count") or 0) <= 0:
        raise SystemExit("向量库为空：请先入库，或用默认 --mode lexical")
    return [str(h.get("title") or "") for h in store.search(question, top_k=top_k, min_score=0.0)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default=str(ROOT / "configs" / "eval_set_7scenes.json"))
    parser.add_argument("--kb", default=str(ROOT / "data" / "kb" / "eval_core"))
    parser.add_argument("--mode", choices=["lexical", "retrieval"], default="lexical")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--out", default=str(ROOT / "data" / "logs" / "eval_citation_report.json"))
    args = parser.parse_args()

    data = json.loads(Path(args.set).read_text(encoding="utf-8"))
    items = data.get("items") or []
    target = float(data.get("target_citation_hit_rate") or 0.9)

    docs: list[dict] = []
    if args.mode == "lexical":
        docs = _load_kb_docs(Path(args.kb))
        if not docs:
            raise SystemExit(f"知识库为空: {args.kb}")

    results = []
    by_scene: dict[str, list[bool]] = defaultdict(list)

    for it in items:
        q = it["question"]
        expected = list(it.get("expected_laws") or [])
        if args.mode == "lexical":
            titles = _lexical_top(q, docs, args.top_k)
            covered = _hit(" ".join(d["title"] for d in docs), expected)
            ranked = _hit(" ".join(titles), expected)
            ok = ranked  # 主指标：粗检索 top 是否含期望法
        else:
            titles = _retrieval_top(q, args.top_k)
            covered = True
            ranked = _hit(" ".join(titles), expected)
            ok = ranked

        by_scene[it.get("scene") or "未分类"].append(ok)
        results.append(
            {
                "id": it.get("id"),
                "scene": it.get("scene"),
                "question": q,
                "expected_laws": expected,
                "hit": ok,
                "kb_covered": covered,
                "top_titles": titles[:5],
            }
        )

    total = len(results)
    hits_n = sum(1 for r in results if r["hit"])
    covered_n = sum(1 for r in results if r.get("kb_covered"))
    rate = (hits_n / total) if total else 0.0
    cover_rate = (covered_n / total) if total else 0.0
    scene_rates = {
        s: (sum(1 for x in xs if x) / len(xs) if xs else 0.0) for s, xs in by_scene.items()
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "top_k": args.top_k,
        "total": total,
        "hits": hits_n,
        "hit_rate": round(rate, 4),
        "kb_cover_rate": round(cover_rate, 4),
        "target": target,
        "pass": rate >= target,
        "scene_rates": {k: round(v, 4) for k, v in scene_rates.items()},
        "items": results,
        "note": "主指标 hit_rate=粗检索 top 含期望法；kb_cover_rate=评测集法规是否收入 eval_core。",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"mode={args.mode} total={total} hits={hits_n} "
        f"hit_rate={rate:.2%} cover={cover_rate:.2%} pass={report['pass']}"
    )
    for s, v in sorted(scene_rates.items()):
        print(f"  {s}: {v:.2%}")
    print(f"report -> {out}")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
