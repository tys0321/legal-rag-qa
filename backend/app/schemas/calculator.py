"""法律计算器请求/响应。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CalculatorField(BaseModel):
    key: str
    label: str
    type: str = "number"
    required: bool = False
    placeholder: str = ""
    options: list[str] = Field(default_factory=list)


class CalculatorSummary(BaseModel):
    id: str
    name: str
    category: str = ""
    description: str = ""
    field_count: int = 0


class CalculatorDetail(BaseModel):
    id: str
    name: str
    category: str = ""
    description: str = ""
    fields: list[CalculatorField] = Field(default_factory=list)
    notice: str = ""


class CalculatorListOut(BaseModel):
    version: int = 1
    total: int = 0
    notice: str = ""
    items: list[CalculatorSummary] = Field(default_factory=list)


class CalculatorRunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class CalculatorLine(BaseModel):
    label: str
    value: str
    amount: float | None = None


class CalculatorRunOut(BaseModel):
    id: str
    name: str
    category: str = ""
    total: float
    currency: str = "CNY"
    lines: list[CalculatorLine] = Field(default_factory=list)
    formula: str = ""
    notice: str = "估算仅供参考"
    warnings: list[str] = Field(default_factory=list)
    inputs_used: dict[str, Any] = Field(default_factory=dict)
