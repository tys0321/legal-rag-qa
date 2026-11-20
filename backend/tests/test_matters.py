"""案件工作区 CRUD / 期限 / 挂接记录。"""
from __future__ import annotations

import pytest

from app.repositories import database as db
from app.repositories import matters as repo
from app.services import matters as svc
from app.services import user_records as records


@pytest.fixture()
def uid() -> int:
    try:
        db.init_db()
    except Exception:
        pytest.skip("MySQL 不可用")
    row = db.query_one("SELECT id FROM users WHERE username = ?", ("matter_user",))
    if row:
        uid = int(row["id"])
    else:
        cur = db.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            ("matter_user", "x", "y", "user"),
        )
        uid = int(cur.lastrowid)
    # 清理该用户案件
    for m in repo.list_matters(uid):
        repo.delete_matter(uid, int(m["id"]))
    db.execute("DELETE FROM user_records WHERE user_id = ?", (uid,))
    return uid


def test_matter_crud_and_deadline(uid: int) -> None:
    m = repo.create_matter(uid, title="张某劳动争议", case_no="(2024)民初1号", cause="劳动争议", role_mode="lawyer")
    assert m and m["title"] == "张某劳动争议"
    mid = int(m["id"])

    listed = repo.list_matters(uid, "lawyer")
    assert any(int(x["id"]) == mid for x in listed)

    updated = repo.update_matter(uid, mid, {"status": "closed", "title": "张某劳动争议-结"})
    assert updated and updated["status"] == "closed"
    assert updated["title"] == "张某劳动争议-结"

    dl = repo.add_deadline(uid, mid, label="上诉期限", due_date="2020-01-01")
    assert dl and dl["label"] == "上诉期限"
    assert dl["overdue"] is True

    dls = repo.list_deadlines(uid, mid)
    assert len(dls) == 1
    toggled = repo.update_deadline(uid, mid, int(dl["id"]), {"done": True})
    assert toggled and toggled["done"] is True

    art = repo.add_artifact(uid, mid, kind="note", title="备注", payload={"text": "已约谈"})
    assert art and art["kind"] == "note"
    arts = repo.list_artifacts(uid, mid)
    assert len(arts) == 1

    assert repo.delete_deadline(uid, mid, int(dl["id"]))
    assert repo.delete_artifact(uid, mid, int(art["id"]))
    assert repo.delete_matter(uid, mid)


def test_link_record_and_extract_fallback(uid: int) -> None:
    m = repo.create_matter(uid, title="李某盗窃审查", role_mode="prosecutor")
    mid = int(m["id"])
    rid = records.save_record(uid, "opinion", "审查草稿", "prosecutor", {"markdown": "## 事实摘要\nx"})
    assert rid
    linked = svc.link_record(uid, mid, int(rid), kind="opinion")
    assert linked and linked["ref_record_id"] == rid

    # 过短应报错
    with pytest.raises(ValueError):
        svc.extract_dossier(uid, mid, text="太短")

    # 无 LLM key 时 chat 可能失败，服务层会降级写入
    art = svc.extract_dossier(
        uid,
        mid,
        text="嫌疑人张三于2023年1月1日在某商场扒窃手机一部，价值约三千元。到案后辩称临时起意。证据有监控与被害人陈述。",
        title="测试抽取",
    )
    assert art and art["kind"] == "extract"
    assert art["payload"].get("dossier_text")
