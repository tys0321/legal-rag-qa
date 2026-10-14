"""轻量律所模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FirmCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)


class FirmInviteRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)


class FirmMemberOut(BaseModel):
    firm_id: int
    user_id: int
    username: str = ""
    role: str = "member"
    joined_at: str = ""


class FirmOut(BaseModel):
    id: int
    name: str
    owner_user_id: int
    created_at: str = ""
    members: list[FirmMemberOut] = Field(default_factory=list)


class FirmInviteOut(BaseModel):
    firm_id: int
    user_id: int
    username: str
    role: str = "member"
