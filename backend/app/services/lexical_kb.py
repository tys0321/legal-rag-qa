"""向量库为空时的词面检索兜底：扫描 data/kb（含 eval_core）。"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings

_CACHE: list[dict] | None = None


def _kb_roots() -> list[Path]:
    """知识库目录；子目录已被父目录覆盖时不重复扫描。"""
    candidates = [settings.kb_source_dir, PROJECT_ROOT / "data" / "kb" / "eval_core"]
    roots: list[Path] = []
    for p in candidates:
        if not p.exists():
            continue
        rp = p.resolve()
        if any(rp == e or e in rp.parents for e in roots):
            continue
        roots = [e for e in roots if rp not in e.parents]
        roots.append(rp)
    return roots


def _ngrams(text: str) -> set[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", text)
    toks: set[str] = set()
    for n in (2, 3, 4):
        for i in range(0, max(0, len(chars) - n + 1)):
            toks.add("".join(chars[i : i + n]))
    return toks


def load_docs(force: bool = False) -> list[dict]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    docs: list[dict] = []
    for root in _kb_roots():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".markdown"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            title = path.stem
            m = re.search(r"^#\s+(.+)$", text, re.M)
            if m:
                title = m.group(1).strip()
            # 按条款粗切
            parts = re.split(r"(?=第[一二三四五六七八九十百千零〇两\d]+条)", text)
            if len(parts) <= 1:
                docs.append(
                    {
                        "id": f"lex:{path.name}:0",
                        "doc_id": path.stem,
                        "title": title,
                        "category": "法律",
                        "article": "",
                        "page": 0,
                        "text": text[:1200],
                        "score": 0.0,
                        "match": "lexical",
                        "effective_status": "现行有效",
                        "effective_detail": "",
                    }
                )
                continue
            for i, part in enumerate(parts):
                part = part.strip()
                if len(part) < 8:
                    continue
                am = re.match(r"(第[一二三四五六七八九十百千零〇两\d]+条)", part)
                article = am.group(1) if am else ""
                docs.append(
                    {
                        "id": f"lex:{path.name}:{i}",
                        "doc_id": path.stem,
                        "title": title,
                        "category": "法律",
                        "article": article,
                        "page": 0,
                        "text": part[:1200],
                        "score": 0.0,
                        "match": "lexical",
                        "effective_status": "现行有效",
                        "effective_detail": "",
                    }
                )
    _CACHE = docs
    return docs


def lexical_search(query: str, top_k: int = 8) -> list[dict]:
    docs = load_docs()
    if not docs:
        return []
    toks = _ngrams(query)
    scored: list[tuple[float, dict]] = []
    for d in docs:
        blob = d["title"] + "\n" + d["text"]
        score = 0.0
        for tok in toks:
            if tok in d["title"]:
                score += 4
            elif tok in (d.get("article") or ""):
                score += 3
            elif tok in blob:
                score += 1
        if score > 0:
            item = dict(d)
            item["score"] = round(score, 2)
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1]["title"]))
    return [x for _, x in scored[:top_k]]
