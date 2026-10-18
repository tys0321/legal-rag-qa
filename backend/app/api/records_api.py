"""用户工作记录。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.services import user_records as records

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/records")
def list_user_records(kind: str, user: dict = Depends(get_current_user)) -> dict:
    if kind not in records.KINDS:
        raise AppError("未知记录类型", 400)
    return {"items": records.list_records(int(user["id"]), kind)}


@router.get("/records/{record_id}")
def get_user_record(record_id: int, user: dict = Depends(get_current_user)) -> dict:
    row = records.get_record(int(user["id"]), record_id)
    if not row:
        raise AppError("记录不存在", 404)
    return row


@router.delete("/records/{record_id}")
def delete_user_record(record_id: int, user: dict = Depends(get_current_user)) -> dict:
    ok = records.delete_record(int(user["id"]), record_id)
    if not ok:
        raise AppError("记录不存在", 404)
    return {"ok": True}
