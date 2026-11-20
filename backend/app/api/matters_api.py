"""案件工作区 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories import matters as repo
from app.schemas.matter import (
    ArtifactCreate,
    ArtifactOut,
    DeadlineCreate,
    DeadlineOut,
    DeadlineUpdate,
    ExtractRequest,
    LinkRecordRequest,
    MatterCreate,
    MatterOut,
    MatterUpdate,
)
from app.services import matters as svc

router = APIRouter(prefix="/api", tags=["matters"])


def _matter_out(row: dict) -> MatterOut:
    return MatterOut(
        id=int(row["id"]),
        title=row.get("title") or "",
        case_no=row.get("case_no") or "",
        cause=row.get("cause") or "",
        role_mode=row.get("role_mode") or "lawyer",
        status=row.get("status") or "open",
        meta=row.get("meta") if isinstance(row.get("meta"), dict) else {},
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
        artifact_count=int(row.get("artifact_count") or 0),
        deadline_count=int(row.get("deadline_count") or 0),
        overdue_count=int(row.get("overdue_count") or 0),
    )


def _artifact_out(row: dict) -> ArtifactOut:
    return ArtifactOut(
        id=int(row["id"]),
        matter_id=int(row["matter_id"]),
        kind=row.get("kind") or "",
        title=row.get("title") or "",
        ref_record_id=row.get("ref_record_id"),
        payload=row.get("payload") if isinstance(row.get("payload"), dict) else {},
        created_at=str(row.get("created_at") or ""),
    )


def _deadline_out(row: dict) -> DeadlineOut:
    return DeadlineOut(
        id=int(row["id"]),
        matter_id=int(row["matter_id"]),
        label=row.get("label") or "",
        due_date=row.get("due_date"),
        calc_key=row.get("calc_key") or "",
        done=bool(row.get("done")),
        overdue=bool(row.get("overdue")),
        created_at=str(row.get("created_at") or ""),
    )


@router.get("/matters", response_model=list[MatterOut])
def list_matters(role_mode: str = "", user: dict = Depends(get_current_user)) -> list[MatterOut]:
    rows = repo.list_matters(int(user["id"]), role_mode or None)
    return [_matter_out(r) for r in rows]


@router.post("/matters", response_model=MatterOut)
def create_matter(body: MatterCreate, user: dict = Depends(get_current_user)) -> MatterOut:
    row = repo.create_matter(
        int(user["id"]),
        title=body.title,
        case_no=body.case_no,
        cause=body.cause,
        role_mode=body.role_mode,
        status=body.status,
        meta=body.meta,
    )
    return _matter_out(row)


@router.get("/matters/{matter_id}", response_model=MatterOut)
def get_matter(matter_id: int, user: dict = Depends(get_current_user)) -> MatterOut:
    row = repo.get_matter(int(user["id"]), matter_id)
    if not row:
        raise AppError("案件不存在", 404)
    return _matter_out(row)


@router.patch("/matters/{matter_id}", response_model=MatterOut)
def update_matter(
    matter_id: int,
    body: MatterUpdate,
    user: dict = Depends(get_current_user),
) -> MatterOut:
    fields = body.model_dump(exclude_unset=True)
    if "meta" in fields:
        pass
    row = repo.update_matter(int(user["id"]), matter_id, fields)
    if not row:
        raise AppError("案件不存在", 404)
    return _matter_out(row)


@router.delete("/matters/{matter_id}")
def delete_matter(matter_id: int, user: dict = Depends(get_current_user)) -> dict:
    ok = repo.delete_matter(int(user["id"]), matter_id)
    if not ok:
        raise AppError("案件不存在", 404)
    return {"ok": True}


@router.get("/matters/{matter_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(matter_id: int, user: dict = Depends(get_current_user)) -> list[ArtifactOut]:
    if not repo.get_matter(int(user["id"]), matter_id):
        raise AppError("案件不存在", 404)
    return [_artifact_out(r) for r in repo.list_artifacts(int(user["id"]), matter_id)]


@router.post("/matters/{matter_id}/artifacts", response_model=ArtifactOut)
def add_artifact(
    matter_id: int,
    body: ArtifactCreate,
    user: dict = Depends(get_current_user),
) -> ArtifactOut:
    row = repo.add_artifact(
        int(user["id"]),
        matter_id,
        kind=body.kind,
        title=body.title,
        ref_record_id=body.ref_record_id,
        payload=body.payload,
    )
    if not row:
        raise AppError("案件不存在", 404)
    return _artifact_out(row)


@router.delete("/matters/{matter_id}/artifacts/{artifact_id}")
def delete_artifact(
    matter_id: int,
    artifact_id: int,
    user: dict = Depends(get_current_user),
) -> dict:
    ok = repo.delete_artifact(int(user["id"]), matter_id, artifact_id)
    if not ok:
        raise AppError("材料不存在", 404)
    return {"ok": True}


@router.get("/matters/{matter_id}/deadlines", response_model=list[DeadlineOut])
def list_deadlines(matter_id: int, user: dict = Depends(get_current_user)) -> list[DeadlineOut]:
    if not repo.get_matter(int(user["id"]), matter_id):
        raise AppError("案件不存在", 404)
    return [_deadline_out(r) for r in repo.list_deadlines(int(user["id"]), matter_id)]


@router.post("/matters/{matter_id}/deadlines", response_model=DeadlineOut)
def add_deadline(
    matter_id: int,
    body: DeadlineCreate,
    user: dict = Depends(get_current_user),
) -> DeadlineOut:
    row = repo.add_deadline(
        int(user["id"]),
        matter_id,
        label=body.label,
        due_date=body.due_date,
        calc_key=body.calc_key,
        done=body.done,
    )
    if not row:
        raise AppError("案件不存在", 404)
    return _deadline_out(row)


@router.patch("/matters/{matter_id}/deadlines/{deadline_id}", response_model=DeadlineOut)
def update_deadline(
    matter_id: int,
    deadline_id: int,
    body: DeadlineUpdate,
    user: dict = Depends(get_current_user),
) -> DeadlineOut:
    row = repo.update_deadline(
        int(user["id"]),
        matter_id,
        deadline_id,
        body.model_dump(exclude_unset=True),
    )
    if not row:
        raise AppError("期限不存在", 404)
    return _deadline_out(row)


@router.delete("/matters/{matter_id}/deadlines/{deadline_id}")
def delete_deadline(
    matter_id: int,
    deadline_id: int,
    user: dict = Depends(get_current_user),
) -> dict:
    ok = repo.delete_deadline(int(user["id"]), matter_id, deadline_id)
    if not ok:
        raise AppError("期限不存在", 404)
    return {"ok": True}


@router.post("/matters/{matter_id}/link-record", response_model=ArtifactOut)
def link_record(
    matter_id: int,
    body: LinkRecordRequest,
    user: dict = Depends(get_current_user),
) -> ArtifactOut:
    row = svc.link_record(
        int(user["id"]),
        matter_id,
        body.record_id,
        kind=body.kind,
        title=body.title,
    )
    if not row:
        raise AppError("案件或记录不存在", 404)
    return _artifact_out(row)


@router.post("/matters/{matter_id}/extract", response_model=ArtifactOut)
def extract_text(
    matter_id: int,
    body: ExtractRequest,
    user: dict = Depends(get_current_user),
) -> ArtifactOut:
    try:
        row = svc.extract_dossier(
            int(user["id"]),
            matter_id,
            text=body.text,
            title=body.title,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    if not row:
        raise AppError("案件不存在", 404)
    return _artifact_out(row)


@router.post("/matters/{matter_id}/extract-upload", response_model=ArtifactOut)
async def extract_upload(
    matter_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> ArtifactOut:
    data = await file.read()
    if not data:
        raise AppError("空文件", 400)
    try:
        row = svc.extract_from_upload(
            int(user["id"]),
            matter_id,
            filename=file.filename or "upload.txt",
            data=data,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    if not row:
        raise AppError("案件不存在", 404)
    return _artifact_out(row)
