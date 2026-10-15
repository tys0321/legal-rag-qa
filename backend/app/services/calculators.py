"""法律计算器：配置化参数 + 确定性公式估算。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.core.errors import AppError

_CATALOG_PATH = PROJECT_ROOT / "configs" / "calculators.json"
_CACHE: dict | None = None

DEFAULT_NOTICE = "估算仅供参考，不构成正式法律意见或费用核定；具体以法院/仲裁机构认定及当地政策为准。"

# 一次性伤残补助金：月数（条例简版）
_INJURY_MONTHS = {1: 27, 2: 25, 3: 23, 4: 21, 5: 18, 6: 16, 7: 13, 8: 11, 9: 9, 10: 7}


def load_catalog() -> dict:
    global _CACHE
    if _CACHE is None:
        path = Path(_CATALOG_PATH)
        if not path.exists():
            raise AppError("计算器配置缺失", 503)
        _CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE


def reload_catalog() -> dict:
    global _CACHE
    _CACHE = None
    return load_catalog()


def notice() -> str:
    return str(load_catalog().get("notice") or DEFAULT_NOTICE)


def params() -> dict:
    return dict(load_catalog().get("params") or {})


def _calculators() -> list[dict]:
    return list(load_catalog().get("calculators") or [])


def list_calculators() -> dict:
    items = []
    for c in _calculators():
        fields = c.get("fields") or []
        items.append(
            {
                "id": c["id"],
                "name": c.get("name") or c["id"],
                "category": c.get("category") or "",
                "description": c.get("description") or "",
                "field_count": len(fields),
            }
        )
    return {
        "version": int(load_catalog().get("version") or 1),
        "total": len(items),
        "notice": notice(),
        "items": items,
    }


def get_calculator(calc_id: str) -> dict:
    for c in _calculators():
        if c.get("id") == calc_id:
            return c
    raise AppError(f"未找到计算器: {calc_id}", 404)


def get_calculator_detail(calc_id: str) -> dict:
    c = get_calculator(calc_id)
    fields = []
    for f in c.get("fields") or []:
        fields.append(
            {
                "key": f.get("key") or "",
                "label": f.get("label") or f.get("key") or "",
                "type": f.get("type") or "number",
                "required": bool(f.get("required")),
                "placeholder": f.get("placeholder") or "",
                "options": list(f.get("options") or []),
            }
        )
    return {
        "id": c["id"],
        "name": c.get("name") or c["id"],
        "category": c.get("category") or "",
        "description": c.get("description") or "",
        "fields": fields,
        "notice": notice(),
    }


def _num(inputs: dict[str, Any], key: str, default: float = 0.0) -> float:
    raw = inputs.get(key, default)
    if raw is None or raw == "":
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise AppError(f"参数「{key}」须为数字", 400) from exc


def _yes(inputs: dict[str, Any], key: str, default: bool = False) -> bool:
    raw = inputs.get(key)
    if raw is None or raw == "":
        return default
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    return s in {"1", "true", "yes", "是", "y"}


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def _litigation_fee(amount: float) -> float:
    """财产案件受理费分段累进（元）。"""
    a = max(0.0, amount)
    if a <= 10000:
        return 50.0
    fee = 50.0
    brackets = [
        (100000, 0.025),
        (200000, 0.02),
        (500000, 0.015),
        (1000000, 0.01),
        (2000000, 0.009),
        (5000000, 0.008),
        (10000000, 0.007),
        (20000000, 0.006),
        (float("inf"), 0.005),
    ]
    prev = 10000.0
    for upper, rate in brackets:
        if a <= prev:
            break
        segment = min(a, upper) - prev
        if segment > 0:
            fee += segment * rate
        prev = upper
        if a <= upper:
            break
    return _money(fee)


def _run_litigation(inputs: dict[str, Any]) -> dict:
    amount = _num(inputs, "amount")
    if amount < 0:
        raise AppError("标的金额不能为负", 400)
    base = _litigation_fee(amount)
    half = _yes(inputs, "half_fee", False)
    total = _money(base / 2 if half else base)
    lines = [
        {"label": "标的金额", "value": f"{_money(amount):,.2f} 元", "amount": _money(amount)},
        {"label": "受理费（全额）", "value": f"{base:,.2f} 元", "amount": base},
    ]
    if half:
        lines.append({"label": "减半后应交", "value": f"{total:,.2f} 元", "amount": total})
    return {
        "total": total,
        "lines": lines,
        "formula": "财产案件受理费分段累进；可选减半",
        "warnings": [],
        "inputs_used": {"amount": amount, "half_fee": half},
    }


def _run_interest(inputs: dict[str, Any]) -> dict:
    p = params()
    principal = _num(inputs, "principal")
    annual_rate = _num(inputs, "annual_rate")
    days = _num(inputs, "days")
    if principal < 0 or days < 0:
        raise AppError("本金与天数不能为负", 400)
    if annual_rate < 0:
        raise AppError("年利率不能为负", 400)
    cap = _yes(inputs, "cap_by_lpr", True)
    lpr = float(p.get("lpr_annual_rate") or 0.031)
    mult = float(p.get("private_lend_max_multiplier") or 4.0)
    cap_rate = lpr * mult
    applied = annual_rate
    warnings: list[str] = []
    if cap and annual_rate > cap_rate:
        applied = cap_rate
        warnings.append(
            f"约定年利率 {annual_rate:.4f} 超过 LPR×{mult:g}（{cap_rate:.4f}），已按上限计算"
        )
    interest = _money(principal * applied * days / 365.0)
    return {
        "total": interest,
        "lines": [
            {"label": "本金", "value": f"{_money(principal):,.2f} 元", "amount": _money(principal)},
            {"label": "适用年利率", "value": f"{applied:.4%}", "amount": None},
            {"label": "计息天数", "value": f"{days:g} 天", "amount": None},
            {"label": "利息", "value": f"{interest:,.2f} 元", "amount": interest},
        ],
        "formula": "利息 = 本金 × 适用年利率 × 天数 / 365",
        "warnings": warnings,
        "inputs_used": {
            "principal": principal,
            "annual_rate": annual_rate,
            "applied_rate": applied,
            "days": days,
            "cap_by_lpr": cap,
            "lpr_annual_rate": lpr,
            "cap_rate": cap_rate,
        },
    }


def _run_work_injury(inputs: dict[str, Any]) -> dict:
    p = params()
    wage = _num(inputs, "monthly_wage", float(p.get("default_monthly_wage") or 6000))
    grade = int(_num(inputs, "grade"))
    avg = _num(inputs, "avg_wage", float(p.get("default_avg_monthly_wage") or 8000))
    if wage <= 0:
        raise AppError("本人工资须大于 0", 400)
    if grade < 1 or grade > 10:
        raise AppError("伤残等级须为 1-10", 400)
    # 工资上下限：本人工资高于社平 300% 的按 300%，低于 60% 的按 60%（简版）
    capped = wage
    warnings: list[str] = []
    if avg > 0:
        if wage > avg * 3:
            capped = avg * 3
            warnings.append("本人工资超过统筹地区社平工资 300%，已按 300% 封顶")
        elif wage < avg * 0.6:
            capped = avg * 0.6
            warnings.append("本人工资低于统筹地区社平工资 60%，已按 60% 保底")
    months = _INJURY_MONTHS[grade]
    lump = _money(capped * months)
    # 5-6 级简版：一次性伤残就业补助金（地方标准差异大，仅给框架估算=6个月）
    extra_lines = []
    extra = 0.0
    if grade <= 6:
        extra = _money(capped * 6)
        extra_lines.append(
            {
                "label": "一次性伤残就业补助金（简版估算）",
                "value": f"{extra:,.2f} 元",
                "amount": extra,
            }
        )
        warnings.append("5-6 级就业补助金地方标准差异大，此处按 6 个月工资简估")
    total = _money(lump + extra)
    lines = [
        {"label": "计发月工资", "value": f"{_money(capped):,.2f} 元", "amount": _money(capped)},
        {"label": "伤残等级", "value": f"{grade} 级（{months} 个月）", "amount": None},
        {"label": "一次性伤残补助金", "value": f"{lump:,.2f} 元", "amount": lump},
        *extra_lines,
    ]
    return {
        "total": total,
        "lines": lines,
        "formula": "一次性伤残补助金 = 计发月工资 × 对应月数（+ 简版就业补助）",
        "warnings": warnings,
        "inputs_used": {
            "monthly_wage": wage,
            "capped_wage": capped,
            "grade": grade,
            "avg_wage": avg,
            "months": months,
        },
    }


def _run_traffic_medical(inputs: dict[str, Any]) -> dict:
    keys = [
        ("hospital", "住院/门诊医疗费"),
        ("medicine", "药品费"),
        ("nursing", "护理费"),
        ("nutrition", "营养费"),
        ("transport", "交通费"),
        ("other", "其他合理费用"),
    ]
    lines = []
    total = 0.0
    used: dict[str, float] = {}
    for key, label in keys:
        v = _money(max(0.0, _num(inputs, key, 0)))
        used[key] = v
        if v > 0 or key == "hospital":
            lines.append({"label": label, "value": f"{v:,.2f} 元", "amount": v})
            total += v
    total = _money(total)
    return {
        "total": total,
        "lines": lines
        + [{"label": "合计", "value": f"{total:,.2f} 元", "amount": total}],
        "formula": "医疗相关费用分项累加",
        "warnings": ["未包含伤残赔偿金、死亡赔偿金、精神损害抚慰金等"],
        "inputs_used": used,
    }


def _run_overtime(inputs: dict[str, Any]) -> dict:
    wage = _num(inputs, "monthly_wage")
    if wage <= 0:
        raise AppError("月工资须大于 0", 400)
    wd = max(0.0, _num(inputs, "weekday_hours", 0))
    rd = max(0.0, _num(inputs, "restday_hours", 0))
    hd = max(0.0, _num(inputs, "holiday_hours", 0))
    days = _num(inputs, "workdays_per_month", 21.75)
    if days <= 0:
        raise AppError("月计薪天数须大于 0", 400)
    hourly = wage / days / 8.0
    a = _money(hourly * 1.5 * wd)
    b = _money(hourly * 2.0 * rd)
    c = _money(hourly * 3.0 * hd)
    total = _money(a + b + c)
    return {
        "total": total,
        "lines": [
            {"label": "小时工资", "value": f"{_money(hourly):,.4f} 元/时", "amount": _money(hourly)},
            {"label": "工作日加班（×1.5）", "value": f"{a:,.2f} 元", "amount": a},
            {"label": "休息日加班（×2）", "value": f"{b:,.2f} 元", "amount": b},
            {"label": "法定节假日加班（×3）", "value": f"{c:,.2f} 元", "amount": c},
        ],
        "formula": "小时工资=月工资/计薪天数/8；加班费=小时工资×倍率×小时数",
        "warnings": ["休息日已调休的可不支付加班费，以用人单位安排为准"],
        "inputs_used": {
            "monthly_wage": wage,
            "weekday_hours": wd,
            "restday_hours": rd,
            "holiday_hours": hd,
            "workdays_per_month": days,
            "hourly_wage": hourly,
        },
    }


_RUNNERS = {
    "litigation_fee": _run_litigation,
    "private_lend_interest": _run_interest,
    "work_injury": _run_work_injury,
    "traffic_medical": _run_traffic_medical,
    "overtime_pay": _run_overtime,
}


def run_calculator(calc_id: str, inputs: dict[str, Any] | None = None) -> dict:
    c = get_calculator(calc_id)
    runner = _RUNNERS.get(calc_id)
    if not runner:
        raise AppError(f"计算器未实现: {calc_id}", 501)
    # 必填校验
    raw = inputs or {}
    for f in c.get("fields") or []:
        if f.get("required"):
            key = f.get("key") or ""
            val = raw.get(key)
            if val is None or str(val).strip() == "":
                raise AppError(f"缺少必填参数: {f.get('label') or key}", 400)
    result = runner(raw)
    return {
        "id": c["id"],
        "name": c.get("name") or c["id"],
        "category": c.get("category") or "",
        "total": float(result["total"]),
        "currency": "CNY",
        "lines": result.get("lines") or [],
        "formula": result.get("formula") or "",
        "notice": notice(),
        "warnings": result.get("warnings") or [],
        "inputs_used": result.get("inputs_used") or {},
    }
