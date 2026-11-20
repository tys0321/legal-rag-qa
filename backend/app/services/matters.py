"""案件工作区业务：链接记录、卷宗抽取。"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.repositories import matters as repo
from app.services.llm import chat
from app.services.user_records import get_record

logger = logging.getLogger("app")

EXTRACT_PROMPT = """你是办案辅助助手。请从下列材料中抽取结构化要点，严格按 JSON 输出（不要 Markdown 围栏）：
{{
  "facts": "认定/陈述事实摘要",
  "evidence": "证据清单及证明对象（条目）",
  "defense": "辩解或对方主张",
  "gaps": "缺口、程序瑕疵、待补查事项",
  "focus": "建议的审查/待决焦点一句话"
}}

约束：不得编造材料中没有的事实；材料不足对应字段写「材料不足」；简体中文。

【材料标题】{title}
【材料正文】
{text}
"""


def link_record(
    user_id: int,
    matter_id: int,
    record_id: int,
    *,
    kind: str = "",
    title: str = "",
) -> dict | None:
    rec = get_record(user_id, record_id)
    if not rec:
        return None
    art_kind = (kind or rec.get("kind") or "note")[:32]
    art_title = (title or rec.get("title") or art_kind)[:200]
    return repo.add_artifact(
        user_id,
        matter_id,
        kind=art_kind,
        title=art_title,
        ref_record_id=record_id,
        payload={"record_summary": rec.get("summary") or "", "kind": rec.get("kind")},
    )


def _parse_extract_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {
                "facts": str(data.get("facts") or ""),
                "evidence": str(data.get("evidence") or ""),
                "defense": str(data.get("defense") or ""),
                "gaps": str(data.get("gaps") or ""),
                "focus": str(data.get("focus") or ""),
            }
    except json.JSONDecodeError:
        pass
    return {
        "facts": text[:2000],
        "evidence": "",
        "defense": "",
        "gaps": "",
        "focus": "",
    }


def extract_dossier(
    user_id: int,
    matter_id: int,
    *,
    text: str,
    title: str = "卷宗要点抽取",
) -> dict | None:
    if not repo.get_matter(user_id, matter_id):
        return None
    body = (text or "").strip()
    if len(body) < 20:
        raise ValueError("材料过短，请粘贴更多卷宗/笔录内容")
    prompt = EXTRACT_PROMPT.format(title=title or "材料", text=body[:20000])
    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1800,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("卷宗抽取 LLM 失败: %s", exc)
        raw = json.dumps(
            {
                "facts": body[:800],
                "evidence": "",
                "defense": "",
                "gaps": "自动抽取失败，请人工整理",
                "focus": "",
            },
            ensure_ascii=False,
        )
    parsed = _parse_extract_json(raw)
    dossier_text = (
        f"认定事实：{parsed['facts']}\n"
        f"主要证据（及证明对象）：{parsed['evidence']}\n"
        f"辩解/对方主张：{parsed['defense']}\n"
        f"辩解/缺口：{parsed['gaps']}"
    )
    payload = {
        **parsed,
        "dossier_text": dossier_text,
        "source_len": len(body),
    }
    art = repo.add_artifact(
        user_id,
        matter_id,
        kind="extract",
        title=(title or "卷宗要点抽取")[:200],
        payload=payload,
    )
    return art


def extract_from_upload(
    user_id: int,
    matter_id: int,
    *,
    filename: str,
    data: bytes,
) -> dict | None:
    """保存临时文件并用 chunker 解析后抽取。"""
    from app.core.config import PROJECT_ROOT, settings
    from app.services.chunker import parse_document

    suffix = Path(filename or "upload.txt").suffix.lower() or ".txt"
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise ValueError("仅支持 pdf / docx / txt / md")
    tmp_dir = Path(settings.upload_dir) / "tmp_extract"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / f"m{matter_id}_{user_id}{suffix}"
    path.write_bytes(data)
    try:
        doc = parse_document(path, PROJECT_ROOT / "data")
        text = "\n".join(p for p in (doc.paragraphs or []) if p).strip()
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    if not text:
        raise ValueError("未能从文件中解析出文本")
    return extract_dossier(
        user_id,
        matter_id,
        text=text,
        title=f"抽取·{Path(filename).name}",
    )
