"""案件工作区（matters）请求/响应。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MatterCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    case_no: str = Field("", max_length=64)
    cause: str = Field("", max_length=64)
    role_mode: str = Field("lawyer", max_length=32)
    status: str = Field("open", max_length=32)
    meta: dict[str, Any] = Field(default_factory=dict)


class MatterUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    case_no: str | None = Field(None, max_length=64)
    cause: str | None = Field(None, max_length=64)
    role_mode: str | None = Field(None, max_length=32)
    status: str | None = Field(None, max_length=32)
    meta: dict[str, Any] | None = None


class MatterOut(BaseModel):
    id: int
    title: str
    case_no: str = ""
    cause: str = ""
    role_mode: str = "lawyer"
    status: str = "open"
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    artifact_count: int = 0
    deadline_count: int = 0
    overdue_count: int = 0


class ArtifactCreate(BaseModel):
    kind: str = Field(..., max_length=32)
    title: str = Field("", max_length=200)
    ref_record_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtifactOut(BaseModel):
    id: int
    matter_id: int
    kind: str
    title: str = ""
    ref_record_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class DeadlineCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    due_date: str | None = Field(None, description="YYYY-MM-DD")
    calc_key: str = Field("", max_length=64)
    done: bool = False


class DeadlineUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=200)
    due_date: str | None = None
    calc_key: str | None = None
    done: bool | None = None


class DeadlineOut(BaseModel):
    id: int
    matter_id: int
    label: str
    due_date: str | None = None
    calc_key: str = ""
    done: bool = False
    overdue: bool = False
    created_at: str = ""


class LinkRecordRequest(BaseModel):
    record_id: int
    kind: str = Field("", max_length=32, description="覆盖 kind；空则用记录自身 kind")
    title: str = Field("", max_length=200)


class ExtractRequest(BaseModel):
    text: str = Field("", max_length=50000, description="粘贴的卷宗/材料文本")
    title: str = Field("卷宗要点抽取", max_length=200)
