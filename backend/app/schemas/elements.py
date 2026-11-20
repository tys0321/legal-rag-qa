"""构成要件勾选。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ElementItem(BaseModel):
    id: str
    label: str
    desc: str = ""
    group: str = "构成要件"
    evidence: str = ""


class ChargeSummary(BaseModel):
    key: str
    charge: str
    category: str = ""
    article_hint: str = ""
    element_count: int = 0


class ChargeOut(BaseModel):
    charge: str
    article_hint: str = ""
    category: str = ""
    compare: list[str] = Field(default_factory=list)
    elements: list[ElementItem] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)


class ElementsCheckRequest(BaseModel):
    charge: str = Field(..., min_length=1, max_length=64)
    checked_ids: list[str] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)
    matter_id: int | None = None


class ElementsCheckOut(BaseModel):
    charge: str
    article_hint: str = ""
    category: str = ""
    compare: list[str] = Field(default_factory=list)
    found: bool = True
    elements: list[Any] = Field(default_factory=list)
    groups: list[Any] = Field(default_factory=list)
    missing: list[Any] = Field(default_factory=list)
    checked_ids: list[str] = Field(default_factory=list)
    supplement_text: str = ""
    artifact_id: int | None = None
