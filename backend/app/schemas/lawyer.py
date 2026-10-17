"""律师认证与免责确认模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LawyerApplyRequest(BaseModel):
    license_no: str = Field(..., min_length=4, max_length=64)
    region: str = Field(..., min_length=2, max_length=64)
    specialties: list[str] = Field(default_factory=list)


class LawyerProfileOut(BaseModel):
    user_id: int
    username: str = ""
    license_no: str = ""
    region: str = ""
    specialties: list[str] = []
    license_files: list[str] = []
    status: str = "none"
    reject_reason: str = ""
    access: str = "none"  # none|pending_readonly|approved|rejected
    reviewed_at: str = ""


class LawyerReviewRequest(BaseModel):
    approve: bool
    reason: str = ""


class LawyerRevokeRequest(BaseModel):
    reason: str = "管理员撤销认证"


class DisclaimerStatusOut(BaseModel):
    acked: bool


class DisclaimerAckOut(BaseModel):
    ok: bool = True
