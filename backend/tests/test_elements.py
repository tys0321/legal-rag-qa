"""罪名构成要件勾选。"""
from __future__ import annotations

from app.services import elements as svc
from app.services.contract_review import _findings, _parse_finding_line


def test_list_and_get_charges() -> None:
    charges = svc.list_charges()
    assert len(charges) >= 20
    names = [c["key"] for c in charges]
    assert "盗窃" in names
    assert "受贿" in names
    assert "帮助信息网络犯罪活动" in names
    info = svc.get_charge("盗窃")
    assert info and len(info["elements"]) >= 8
    assert any(e.get("group") == "程序审查" for e in info["elements"])
    assert any(e.get("evidence") for e in info["elements"])


def test_check_missing_generates_supplement() -> None:
    info = svc.get_charge("诈骗")
    assert info
    ids = [info["elements"][0]["id"]]
    result = svc.check_elements("诈骗", ids, {"deceive": "仅有聊天记录"})
    assert result["found"] is True
    assert len(result["missing"]) == len(info["elements"]) - 1
    assert "补侦" in result["supplement_text"] or "补查" in result["supplement_text"]
    assert "建议调取" in result["supplement_text"]
    assert "此罪彼罪" in result["supplement_text"] or "合同诈骗" in result["supplement_text"]
    assert result["groups"]


def test_unknown_charge() -> None:
    result = svc.check_elements("不存在的罪", [])
    assert result["found"] is False
    assert "未收录" in result["supplement_text"]


def test_contract_finding_parse() -> None:
    row = _parse_finding_line("【条款：违约金】风险：过高｜建议：调至30%｜等级：高")
    assert row["clause"] == "违约金"
    assert "过高" in row["risk"]
    assert "30%" in row["suggestion"]
    assert row["severity"] == "高"

    md = """## 风险点
- 【条款：管辖】风险：约定不明｜建议：写明法院｜等级：中
- 普通一行风险

## 法规对照
- [1] 合同法

## 审查备忘录
- 请复核

## 免责声明
x
"""
    findings = _findings(md)
    assert len(findings) == 2
    assert findings[0]["clause"] == "管辖"
    assert findings[1]["clause"] == "未标明条款"
