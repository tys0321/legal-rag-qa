// 律师案源广场：匹配列表 / 认领 / 站内信 / 模拟中间号

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LeadItem } from "../api/types";

interface Props {
  readonlyMode: boolean;
  scope?: "plaza" | "firm";
}

export default function LeadPlaza({ readonlyMode, scope = "plaza" }: Props) {
  const [items, setItems] = useState<LeadItem[]>([]);
  const [scene, setScene] = useState("");
  const [region, setRegion] = useState("");
  const [active, setActive] = useState<LeadItem | null>(null);
  const [inboxMsg, setInboxMsg] = useState("您好，我是承办律师，方便进一步沟通吗？");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = () => {
    setMsg("");
    api
      .listLeads({
        scope,
        scene: scene || undefined,
        region: region || undefined,
      })
      .then((r) => setItems(r.items))
      .catch((e) => setMsg(e instanceof Error ? e.message : "加载失败"));
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  const openDetail = async (id: number) => {
    try {
      const lead = await api.getLead(id);
      setActive(lead);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "加载详情失败");
    }
  };

  const claim = async () => {
    if (!active || readonlyMode) return;
    setBusy(true);
    try {
      const lead = await api.claimLead(active.id);
      setActive(lead);
      refresh();
      setMsg("认领成功");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "认领失败");
    } finally {
      setBusy(false);
    }
  };

  const contact = async (channel: "inbox" | "virtual_number") => {
    if (!active || readonlyMode) return;
    setBusy(true);
    try {
      const lead = await api.contactLead(active.id, {
        channel,
        message: channel === "inbox" ? inboxMsg : "",
      });
      setActive(lead);
      refresh();
      setMsg(channel === "inbox" ? "站内信已发送（模拟）" : `中间号：${lead.virtual_number}`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "联系失败");
    } finally {
      setBusy(false);
    }
  };

  const closeLead = async () => {
    if (!active || readonlyMode) return;
    setBusy(true);
    try {
      const lead = await api.updateLeadStatus(active.id, "closed");
      setActive(lead);
      refresh();
      setMsg("案源已关闭");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "关闭失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-plaza">
      <div className="lead-toolbar">
        <h3>{scope === "firm" ? "所内案源" : "案源广场"}</h3>
        {scope === "plaza" && (
          <div className="lead-filters">
            <input
              value={scene}
              onChange={(e) => setScene(e.target.value)}
              placeholder="筛选场景"
            />
            <input
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              placeholder="筛选地区"
            />
            <button type="button" className="btn-ghost" onClick={refresh}>
              筛选
            </button>
          </div>
        )}
        {scope === "firm" && (
          <button type="button" className="btn-ghost" onClick={refresh}>
            刷新
          </button>
        )}
      </div>
      {readonlyMode && scope === "plaza" && (
        <div className="risk-banner warn inline">待审只读：可浏览匹配列表，不可认领或联系。</div>
      )}
      {msg && <p className="form-msg">{msg}</p>}
      <ul className="lead-list">
        {items.map((l) => (
          <li key={l.id}>
            <button type="button" className="lead-card" onClick={() => void openDetail(l.id)}>
              <div className="lead-card-top">
                <strong>{l.title}</strong>
                <span className="match-score">匹配 {l.match_score.toFixed(1)}</span>
              </div>
              <div className="lead-meta">
                {l.scene} · {l.region} · {l.status}
              </div>
              <p className="lead-summary">{l.summary.slice(0, 80)}{l.summary.length > 80 ? "…" : ""}</p>
            </button>
          </li>
        ))}
      </ul>
      {items.length === 0 && <p className="muted">暂无案源。</p>}

      {active && (
        <div className="lead-detail">
          <h3>
            #{active.id} {active.title}
          </h3>
          <p className="lead-meta">
            {active.scene} · {active.region} · 联系 {active.contact_masked}
          </p>
          <p>{active.summary}</p>
          <p className="muted">
            状态 <strong>{active.status}</strong>
            {active.virtual_number ? ` · 模拟中间号 ${active.virtual_number}` : ""}
          </p>

          {!readonlyMode && active.status === "open" && (
            <button className="btn-primary" type="button" disabled={busy} onClick={() => void claim()}>
              认领此案源
            </button>
          )}

          {!readonlyMode && (active.status === "claimed" || active.status === "in_contact") && (
            <div className="contact-box">
              <textarea value={inboxMsg} onChange={(e) => setInboxMsg(e.target.value)} rows={3} />
              <div className="btn-row">
                <button className="btn-primary" type="button" disabled={busy} onClick={() => void contact("inbox")}>
                  发站内信
                </button>
                <button className="btn-gold" type="button" disabled={busy} onClick={() => void contact("virtual_number")}>
                  生成模拟中间号
                </button>
                {active.status === "in_contact" && (
                  <button className="btn-ghost" type="button" disabled={busy} onClick={() => void closeLead()}>
                    关闭案源
                  </button>
                )}
              </div>
            </div>
          )}

          <ul className="event-list">
            {(active.events || []).map((e) => (
              <li key={e.id}>
                <span className="event-type">{e.event_type}</span> {e.detail || ""}
                <time>{e.created_at}</time>
              </li>
            ))}
          </ul>
          <button type="button" className="btn-ghost" onClick={() => setActive(null)}>
            关闭详情
          </button>
        </div>
      )}
    </div>
  );
}
