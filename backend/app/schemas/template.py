"""文书模板请求/响应。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateField(BaseModel):
    key: str
    label: str
    type: str = "text"
    required: bool = False
    placeholder: str = ""


class TemplateSummary(BaseModel):
    id: str
    name: str
    category: str = ""
    description: str = ""
    field_count: int = 0


class TemplateDetail(BaseModel):
    id: str
    name: str
    category: str = ""
    description: str = ""
    fields: list[TemplateField] = Field(default_factory=list)
    watermark: str = ""
    disclaimer: str = ""


class TemplateListOut(BaseModel):
    version: int = 1
    total: int = 0
    watermark: str = ""
    items: list[TemplateSummary] = Field(default_factory=list)


class TemplateFillRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict, description="槽位键值")


class TemplateFillOut(BaseModel):
    id: str
    name: str
    category: str = ""
    markdown: str
    watermark: str
    disclaimer: str
    missing_required: list[str] = Field(default_factory=list)
