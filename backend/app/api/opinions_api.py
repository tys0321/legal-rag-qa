"""法律意见书 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.schemas.chat import SourceOut
from app.schemas.opinion import OpinionOut, OpinionRequest
from app.services.audit import log_action
from app.services.opinion import generate_opinion

router = APIRouter(prefix="/api", tags=["opinions"])


@router.post("/opinions/generate", response_model=OpinionOut)
def create_opinion(req: OpinionRequest, user: dict = Depends(get_current_user)) -> OpinionOut:
    try:
        result = generate_opinion(
            fact_summary=req.fact_summary,
            scene=req.scene,
            question=req.question,
            slot_answers=req.slot_answers,
        )
    except RuntimeError as exc:
        raise AppError(str(exc), 503) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"意见书生成失败: {exc}", 500) from exc

    log_action(
        user["id"],
        user["username"],
        "opinion_generate",
        f"scene={req.scene} risk={result.risk_level} blocked={result.blocked}",
    )
    sources_out: list[SourceOut] = []
    for s in result.sources:
        if not isinstance(s, dict):
            continue
        sources_out.append(
            SourceOut(
                id=str(s.get("id") or ""),
                doc_id=str(s.get("doc_id") or ""),
                title=str(s.get("title") or ""),
                category=str(s.get("category") or ""),
                article=str(s.get("article") or ""),
                page=int(s.get("page") or 0),
                text=str(s.get("text") or ""),
                score=float(s.get("score") or 0),
                match=s.get("match"),
                effective_status=str(s.get("effective_status") or ""),
                effective_detail=str(s.get("effective_detail") or ""),
            )
        )
    return OpinionOut(
        scene=result.scene,
        risk_level=result.risk_level,
        blocked=result.blocked,
        title=result.title,
        sections=result.sections,
        markdown=result.markdown,
        sources=sources_out,
        confidence=result.confidence,
        watermark=result.watermark,
        disclaimer=result.disclaimer,
    )
