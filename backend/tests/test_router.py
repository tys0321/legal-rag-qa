"""快慢分流路由测试。"""
from __future__ import annotations

import pytest

from app.services.router import route_query


@pytest.mark.parametrize(
    "query",
    [
        "你好",
        "您好！",
        "hi",
        "谢谢",
        "什么是合同？",
        "什么是合同",
        "什么是民法典",
        "法律和道德的区别",
        "你是谁",
        "你能做什么",
        "打官司的流程是什么",
    ],
)
def test_fast_path(query: str) -> None:
    assert route_query(query) == "fast", f"应走快路径: {query}"


@pytest.mark.parametrize(
    "query",
    [
        "劳动合同法第三十九条是什么",
        "民法典第一百二十条的内容",
        "宪法第三十五条",
        "最高人民法院关于适用民法典的司法解释",
        "行政处罚的时效是多久",
        "工伤赔偿标准是多少",
        "定金和违约金有什么区别",
        "公司辞退员工需要赔偿吗",
        "",
    ],
)
def test_slow_path(query: str) -> None:
    assert route_query(query) == "slow", f"应走慢路径: {query}"
