"""法律计算器 API：列表 / 详情 / 计算。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.calculator import (
    CalculatorDetail,
    CalculatorListOut,
    CalculatorRunOut,
    CalculatorRunRequest,
    CalculatorSummary,
)
from app.services.audit import log_action
from app.services import calculators as calc

router = APIRouter(prefix="/api", tags=["calculators"])


@router.get("/calculators", response_model=CalculatorListOut)
def list_calculators(_user: dict = Depends(get_current_user)) -> CalculatorListOut:
    data = calc.list_calculators()
    return CalculatorListOut(
        version=data["version"],
        total=data["total"],
        notice=data["notice"],
        items=[CalculatorSummary(**x) for x in data["items"]],
    )


@router.get("/calculators/{calc_id}", response_model=CalculatorDetail)
def get_calculator(calc_id: str, _user: dict = Depends(get_current_user)) -> CalculatorDetail:
    data = calc.get_calculator_detail(calc_id)
    return CalculatorDetail(**data)


@router.post("/calculators/{calc_id}", response_model=CalculatorRunOut)
def run_calculator(
    calc_id: str,
    req: CalculatorRunRequest,
    user: dict = Depends(get_current_user),
) -> CalculatorRunOut:
    result = calc.run_calculator(calc_id, req.inputs)
    log_action(
        user["id"],
        user["username"],
        "calculator_run",
        f"id={calc_id} total={result['total']}",
    )
    return CalculatorRunOut(**result)
