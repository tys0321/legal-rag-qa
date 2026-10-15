"""场景分类目录模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SceneCatalogItem(BaseModel):
    id: str
    name: str
    group: str = ""
    status: str = Field(..., description="active|coming_soon")
    alias: str = ""


class SceneCatalogOut(BaseModel):
    version: int = 1
    total: int
    active_count: int
    coming_soon_count: int
    mvp_ids: list[str] = Field(default_factory=list)
    groups: dict[str, int] = Field(default_factory=dict)
    items: list[SceneCatalogItem] = Field(default_factory=list)
