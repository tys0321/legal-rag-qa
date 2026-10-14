"""M2：风险分级与槽位引导。"""
from __future__ import annotations

from app.services.risk import classify_risk
from app.services.slots import detect_scene, missing_slots, try_fill_from_message


def test_l1_blocks_criminal() -> None:
    r = classify_risk("我被刑事拘留了该怎么办，要不要串供")
    assert r.level == "L1"
    assert r.block_answer is True


def test_l2_high_amount() -> None:
    r = classify_risk("对方欠款 80 万不还，我该怎么起诉")
    assert r.level == "L2"
    assert r.force_lawyer_cta is True
    assert r.block_answer is False


def test_l3_normal_labor() -> None:
    r = classify_risk("公司拖欠我两个月工资怎么办")
    assert r.level == "L3"


def test_detect_labor_scene() -> None:
    assert detect_scene("公司拖欠工资还不给加班费") == "劳动用工"


def test_slot_fill_sequence() -> None:
    filled = {}
    filled = try_fill_from_message("劳动用工", "是，签了合同", filled)
    assert filled.get("has_contract")
    miss = missing_slots("劳动用工", filled)
    assert any(m["key"] == "hire_date" for m in miss)
