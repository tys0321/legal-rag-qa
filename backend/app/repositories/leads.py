"""案源仓储：发布、匹配排序、认领、模拟联系与状态机。"""
from __future__ import annotations

import json
import re
from typing import Any

from app.repositories import database as db
from app.repositories import firms as firm_repo
from app.repositories import lawyers as lawyer_repo

VALID_STATUS = {"draft", "open", "claimed", "in_contact", "closed", "cancelled"}

# 允许的状态迁移（含发布方取消、认领后推进）
_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"open", "cancelled"},
    "open": {"claimed", "cancelled"},
    "claimed": {"in_contact", "closed", "cancelled"},
    "in_contact": {"closed", "cancelled"},
    "closed": set(),
    "cancelled": set(),
}

def _active_scene_ids() -> set[str]:
    """案源发布仅接受 MVP 已激活场景（与 scenes_catalog 对齐）。"""
    try:
        from app.services.scenes_catalog import mvp_ids

        ids = set(mvp_ids())
        if ids:
            return ids
    except Exception:  # noqa: BLE001
        pass
    return {
        "劳动用工",
        "房屋租赁",
        "婚姻家事",
        "交通事故",
        "消费维权",
        "行政诉讼",
        "合同纠纷",
    }


def mask_contact(raw: str) -> str:
    """脱敏联系方式：手机保留前3后4，其它保留首尾。"""
    s = (raw or "").strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits.startswith("1"):
        return f"{digits[:3]}****{digits[-4:]}"
    if len(s) <= 4:
        return "*" * len(s)
    return f"{s[:2]}****{s[-2:]}"


def make_virtual_number(lead_id: int) -> str:
    """模拟中间号（不接运营商），演示用固定规则。"""
    a = 8000 + (lead_id % 1000)
    b = 1000 + ((lead_id * 7) % 9000)
    return f"400-{a}-{b}"


def _row_to_lead(row: dict, *, match_score: float = 0.0) -> dict:
    d = dict(row)
    d["firm_visible"] = bool(d.get("firm_visible"))
    d["allow_push"] = bool(d.get("allow_push", 1))
    d["match_score"] = float(match_score)
    d["virtual_number"] = d.get("virtual_number") or ""
    if d.get("claimed_by") is None:
        d["claimed_by"] = None
    return d


def add_event(lead_id: int, actor_id: int | None, event_type: str, detail: str = "") -> dict:
    cur = db.execute(
        """
        INSERT INTO lead_events (lead_id, actor_id, event_type, detail)
        VALUES (?, ?, ?, ?)
        """,
        (lead_id, actor_id, event_type, detail[:2000]),
    )
    eid = cur.lastrowid
    row = db.query_one("SELECT * FROM lead_events WHERE id = ?", (eid,))
    return dict(row) if row else {"id": eid, "lead_id": lead_id, "event_type": event_type, "detail": detail}


def list_events(lead_id: int) -> list[dict]:
    rows = db.query(
        "SELECT * FROM lead_events WHERE lead_id = ? ORDER BY id ASC",
        (lead_id,),
    )
    return [dict(r) for r in rows]


def get_lead(lead_id: int) -> dict | None:
    row = db.query_one("SELECT * FROM leads WHERE id = ?", (lead_id,))
    return _row_to_lead(row) if row else None


def create_lead(
    user_id: int,
    *,
    title: str,
    summary: str,
    scene: str,
    region: str,
    contact: str,
    allow_push: bool = True,
    firm_visible: bool = False,
    publish: bool = True,
) -> dict:
    scene = scene.strip()
    active = _active_scene_ids()
    if scene not in active:
        raise ValueError(f"场景须为已开放 MVP 场景之一: {', '.join(sorted(active))}")
    status = "open" if publish else "draft"
    masked = mask_contact(contact)
    cur = db.execute(
        """
        INSERT INTO leads
        (user_id, scene, region, title, summary, status, firm_visible, contact_masked, allow_push)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            scene,
            region.strip(),
            title.strip(),
            summary.strip(),
            status,
            1 if firm_visible else 0,
            masked,
            1 if allow_push else 0,
        ),
    )
    lead_id = int(cur.lastrowid)
    add_event(lead_id, user_id, "created", f"status={status}")
    if status == "open":
        add_event(lead_id, user_id, "published", "案源进入广场")
    lead = get_lead(lead_id)
    assert lead is not None
    return lead


def match_score(lead: dict, specialties: list[str], lawyer_region: str) -> float:
    """场景 ∩ 擅长 + 地区匹配排序分。"""
    score = 0.0
    scene = (lead.get("scene") or "").strip()
    specs = {s.strip() for s in specialties if s and str(s).strip()}
    if scene and scene in specs:
        score += 10.0
    # 部分重合（如擅长含「劳动」）
    elif scene and any(scene in s or s in scene for s in specs):
        score += 6.0
    lr = (lawyer_region or "").strip()
    rr = (lead.get("region") or "").strip()
    if lr and rr:
        if lr == rr or lr in rr or rr in lr:
            score += 5.0
        elif lr[:2] == rr[:2]:
            score += 2.0
    return score


def list_for_user(user_id: int) -> list[dict]:
    rows = db.query(
        "SELECT * FROM leads WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
        (user_id,),
    )
    return [_row_to_lead(r) for r in rows]


def list_for_lawyer(
    lawyer_user_id: int,
    *,
    scene: str | None = None,
    region: str | None = None,
    include_mine: bool = True,
) -> list[dict]:
    """律师可见：开放案源（按匹配排序）+ 自己已认领。"""
    profile = lawyer_repo.get_profile(lawyer_user_id) or {}
    specialties = list(profile.get("specialties") or [])
    lawyer_region = profile.get("region") or ""

    clauses = ["(status = 'open' OR claimed_by = ?)"]
    params: list[Any] = [lawyer_user_id]
    if scene:
        clauses.append("scene = ?")
        params.append(scene.strip())
    if region:
        clauses.append("region LIKE ?")
        params.append(f"%{region.strip()}%")

    sql = f"SELECT * FROM leads WHERE {' AND '.join(clauses)} ORDER BY id DESC"
    rows = db.query(sql, tuple(params))
    scored: list[tuple[float, dict]] = []
    for r in rows:
        lead = _row_to_lead(r)
        if lead["status"] != "open" and lead.get("claimed_by") != lawyer_user_id:
            if not include_mine:
                continue
        score = match_score(lead, specialties, lawyer_region)
        # 已认领的自己案子保持可见，分数仅用于排序
        if lead.get("claimed_by") == lawyer_user_id:
            score += 0.5
        lead["match_score"] = score
        scored.append((score, lead))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("id") or 0)))
    return [x[1] for x in scored]


def list_open_plaza(
    *,
    scene: str | None = None,
    region: str | None = None,
    viewer_specialties: list[str] | None = None,
    viewer_region: str = "",
) -> list[dict]:
    """广场只读列表（pending 律师浏览用）。"""
    clauses = ["status = 'open'"]
    params: list[Any] = []
    if scene:
        clauses.append("scene = ?")
        params.append(scene.strip())
    if region:
        clauses.append("region LIKE ?")
        params.append(f"%{region.strip()}%")
    rows = db.query(
        f"SELECT * FROM leads WHERE {' AND '.join(clauses)} ORDER BY id DESC",
        tuple(params),
    )
    specs = viewer_specialties or []
    out = []
    for r in rows:
        lead = _row_to_lead(r)
        lead["match_score"] = match_score(lead, specs, viewer_region)
        out.append(lead)
    out.sort(key=lambda x: (-x["match_score"], -(x.get("id") or 0)))
    return out


def claim_lead(lead_id: int, lawyer_user_id: int) -> dict:
    if not lawyer_repo.can_use_lawyer_write(lawyer_user_id):
        raise PermissionError("仅已认证律师可认领案源")
    lead = get_lead(lead_id)
    if not lead:
        raise LookupError("案源不存在")
    if lead["status"] != "open":
        raise ValueError(f"当前状态 {lead['status']} 不可认领")
    if lead["user_id"] == lawyer_user_id:
        raise ValueError("不能认领自己发布的案源")

    cur = db.execute(
        """
        UPDATE leads
        SET status = 'claimed', claimed_by = ?, updated_at = NOW()
        WHERE id = ? AND status = 'open' AND claimed_by IS NULL
        """,
        (lawyer_user_id, lead_id),
    )
    if cur.rowcount == 0:
        raise ValueError("认领失败，案源可能已被他人认领")
    add_event(lead_id, lawyer_user_id, "claimed", f"lawyer={lawyer_user_id}")
    updated = get_lead(lead_id)
    assert updated is not None
    return updated


def contact_lead(
    lead_id: int,
    lawyer_user_id: int,
    *,
    channel: str = "inbox",
    message: str = "",
) -> dict:
    if not lawyer_repo.can_use_lawyer_write(lawyer_user_id):
        raise PermissionError("仅已认证律师可联系案源")
    lead = get_lead(lead_id)
    if not lead:
        raise LookupError("案源不存在")
    if lead.get("claimed_by") != lawyer_user_id:
        raise PermissionError("请先认领该案源后再联系")
    if lead["status"] not in {"claimed", "in_contact"}:
        raise ValueError(f"当前状态 {lead['status']} 不可发起联系")

    channel = (channel or "inbox").strip()
    if channel not in {"inbox", "virtual_number"}:
        raise ValueError("channel 须为 inbox 或 virtual_number")

    payload: dict[str, Any] = {"channel": channel}
    if channel == "virtual_number":
        vnum = lead.get("virtual_number") or make_virtual_number(lead_id)
        db.execute(
            "UPDATE leads SET virtual_number = ?, status = 'in_contact', updated_at = NOW() WHERE id = ?",
            (vnum, lead_id),
        )
        payload["virtual_number"] = vnum
        detail = json.dumps(payload, ensure_ascii=False)
        add_event(lead_id, lawyer_user_id, "virtual_number", detail)
    else:
        msg = (message or "").strip() or "律师通过站内信发起联系（模拟）"
        payload["message"] = msg
        db.execute(
            "UPDATE leads SET status = 'in_contact', updated_at = NOW() WHERE id = ?",
            (lead_id,),
        )
        detail = json.dumps(payload, ensure_ascii=False)
        add_event(lead_id, lawyer_user_id, "inbox", detail)

    updated = get_lead(lead_id)
    assert updated is not None
    return updated


def set_status(lead_id: int, actor_id: int, new_status: str, *, as_admin: bool = False) -> dict:
    new_status = new_status.strip()
    if new_status not in VALID_STATUS:
        raise ValueError(f"非法状态: {new_status}")
    lead = get_lead(lead_id)
    if not lead:
        raise LookupError("案源不存在")
    old = lead["status"]
    if old == new_status:
        return lead
    allowed = _TRANSITIONS.get(old, set())
    if new_status not in allowed and not as_admin:
        raise ValueError(f"不允许从 {old} 转到 {new_status}")

    # 权限：发布者可取消/发布；认领律师可推进；管理员任意（as_admin）
    is_owner = lead["user_id"] == actor_id
    is_claimer = lead.get("claimed_by") == actor_id
    if not as_admin:
        if new_status in {"cancelled"} and not (is_owner or is_claimer):
            raise PermissionError("无权取消该案源")
        if new_status == "open" and not is_owner:
            raise PermissionError("仅发布者可公开案源")
        if new_status in {"closed", "in_contact"} and not is_claimer:
            raise PermissionError("仅认领律师可推进该状态")
        if new_status == "claimed":
            raise ValueError("请使用认领接口 /claim")

    db.execute(
        "UPDATE leads SET status = ?, updated_at = NOW() WHERE id = ?",
        (new_status, lead_id),
    )
    add_event(lead_id, actor_id, "status", f"{old}->{new_status}")
    updated = get_lead(lead_id)
    assert updated is not None
    return updated


def list_for_firm(user_id: int) -> list[dict]:
    """所内可见案源：同所成员认领且 firm_visible=1。"""
    membership = firm_repo.get_membership(user_id)
    if not membership:
        return []
    firm_id = int(membership["firm_id"])
    rows = db.query(
        """
        SELECT l.*
        FROM leads l
        JOIN firm_members fm ON fm.user_id = l.claimed_by AND fm.firm_id = ?
        WHERE l.firm_visible = 1
          AND l.claimed_by IS NOT NULL
        ORDER BY l.updated_at DESC, l.id DESC
        """,
        (firm_id,),
    )
    return [_row_to_lead(r) for r in rows]


def can_view_lead(user: dict, lead: dict) -> bool:
    uid = user["id"]
    if user.get("role") == "admin":
        return True
    if lead["user_id"] == uid:
        return True
    if lead.get("claimed_by") == uid:
        return True
    # 开放案源：律师端可读（含 pending 只读）
    if lead["status"] == "open":
        return True
    # 所内可见：认领律师与查看者同所，且 firm_visible
    if lead.get("firm_visible") and lead.get("claimed_by"):
        if firm_repo.same_firm(uid, int(lead["claimed_by"])):
            return True
    return False
