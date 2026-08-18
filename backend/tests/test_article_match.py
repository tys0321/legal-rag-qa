"""条款匹配（跨法律同名条款消歧）测试。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.repositories.vector_store import VectorStore


class FakeStore(VectorStore):
    """用假数据覆盖向量检索，专注测试条款匹配逻辑。"""

    def __init__(self) -> None:
        super().__init__(Path(tempfile.mkdtemp()))
        self._metas = [
            {"doc_id": "宪法/宪法.docx", "title": "中华人民共和国宪法", "category": "宪法",
             "article": "第三十五条", "page": 0, "text": "公民有言论、出版、集会、结社、游行、示威的自由", "chunk_index": 0},
            {"doc_id": "法律/劳动合同法.docx", "title": "中华人民共和国劳动合同法", "category": "法律",
             "article": "第三十九条", "page": 0, "text": "在试用期间被证明不符合录用条件的，用人单位可以解除劳动合同", "chunk_index": 0},
            {"doc_id": "法律/专利法.docx", "title": "中华人民共和国专利法", "category": "法律",
             "article": "第三十九条", "page": 0, "text": "发明专利申请经实质审查没有发现驳回理由的", "chunk_index": 0},
        ]
        self._ids = [f"{m['doc_id']}#{m['chunk_index']}" for m in self._metas]
        self._id_set = set(self._ids)
        self._vectors = []
        self._loaded = True


def test_article_match_with_law_name_filters() -> None:
    """提到法律名时只匹配该法律的同名条款。"""
    store = FakeStore()
    hits = store._search_by_article("劳动合同法第三十九条是什么", top_k=6)
    titles = {h["title"] for h in hits}
    assert titles == {"中华人民共和国劳动合同法"}
    assert all(h["article"] == "第三十九条" for h in hits)


def test_article_match_without_law_name_all() -> None:
    """未提法律名时返回所有同名条款。"""
    store = FakeStore()
    hits = store._search_by_article("第三十九条是什么", top_k=6)
    assert len(hits) == 2  # 劳动合同法 + 专利法


def test_article_match_chinese_numeral() -> None:
    """阿拉伯数字条款号可匹配中文条款。"""
    store = FakeStore()
    hits = store._search_by_article("劳动合同法第39条", top_k=6)
    assert all(h["article"] == "第三十九条" for h in hits)
