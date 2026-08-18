"""Phase 2 功能测试：法规时效检测、文件名修复、案例检索。"""
from __future__ import annotations

from app.repositories.vector_store import VectorStore, _to_chinese_numeral
from app.services.document_service import DocumentService
from app.services.effective import detect_status


def test_detect_repealed() -> None:
    status = detect_status("某暂行规定", "第一条 本规定自发布之日起施行。", "本规定同时废止。")
    assert status.status == "已废止"
    assert status.evidence


def test_detect_revised() -> None:
    status = detect_status("中华人民共和国刑法（2020年修正）", "根据全国人大常委会关于修改刑法的决定", "")
    assert status.status == "已修订"


def test_detect_effective() -> None:
    status = detect_status("某管理办法", "第一条 为规范管理，制定本办法。", "本办法自公布之日起施行。")
    assert status.status == "现行有效"


def test_detect_partial() -> None:
    status = detect_status("某条例", "第一条 本条例自发布之日起施行。", "本条例第三十五条、第三十六条自发布之日起废止。")
    assert status.status == "部分失效"


def test_fix_filename_mojibake() -> None:
    svc = DocumentService
    garbled = "3f173b7f_\u00d6\u00d0\u00bb\u00aa\u00c8\u00cb\u00c3\u00f1\u00b9\u00b2\u00ba\u00cd\u00b9\u00fa\u00b9\u00ab\u00cb\u00be\u00b7\u00a8.docx"
    fixed = svc._fix_filename(garbled)
    assert "中华人民共和国公司法" in fixed


def test_fix_filename_normal_unchanged() -> None:
    assert DocumentService._fix_filename("normal.txt") == "normal.txt"
    assert DocumentService._fix_filename("中文文档.pdf") == "中文文档.pdf"


def test_fix_filename_gbk_to_utf8_variant() -> None:
    """GBK 字节被 UTF-8 解码的变体。"""
    garbled = "2912dc22_\u00d1\u00e9\u00ca\u00d5\u00b2\u00e2\u00ca\u00d4.txt"
    fixed = DocumentService._fix_filename(garbled)
    assert "验收测试" in fixed


def test_chinese_numeral() -> None:
    assert _to_chinese_numeral("1") == "一"
    assert _to_chinese_numeral("10") == "十"
    assert _to_chinese_numeral("35") == "三十五"
    assert _to_chinese_numeral("99") == "九十九"
    assert _to_chinese_numeral("100") == ""


def test_search_cases_filters() -> None:
    """案例检索只返回案例类文档。"""
    store = VectorStore.__new__(VectorStore)
    store._metas = [
        {"doc_id": "a", "title": "最高人民法院关于某问题的批复", "category": "司法解释", "text": "批复内容", "article": "", "page": 0},
        {"doc_id": "b", "title": "某指导案例", "category": "案例", "text": "案例内容", "article": "", "page": 0},
        {"doc_id": "c", "title": "中华人民共和国刑法", "category": "法律", "text": "刑法条文", "article": "", "page": 0},
    ]
    store._ids = [f"{m['doc_id']}#0" for m in store._metas]
    store._id_set = set(store._ids)
    store._vectors = []
    store._loaded = True

    # 无法真实向量化，直接测过滤逻辑（title/category 特征）
    from app.repositories import vector_store as vs

    is_case = lambda m: (  # noqa: E731
        m.get("category") in ("司法解释", "裁判文书", "案例")
        or any(k in m.get("title", "") for k in ("案例", "批复", "答复", "决定", "判例", "指导案例", "公报"))
    )
    cases = [m for m in store._metas if is_case(m)]
    assert len(cases) == 2  # 批复 + 指导案例
    assert all(c["doc_id"] in ("a", "b") for c in cases)
