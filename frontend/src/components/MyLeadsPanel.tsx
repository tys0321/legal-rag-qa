// 用户查看自己发布的案源

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LeadItem } from "../api/types";

export default function MyLeadsPanel() {
  const [items, setItems] = useState<LeadItem[]>([]);
  const [active, setActive] = useState<LeadItem | null>(null);
  const [err, setErr] = useState("");

  const refresh = () => {
    api
      .listLeads({ scope: "mine" })
      .then((r) => setItems(r.items))
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  };

  useEffect(() => {
    refresh();
  }, []);

  const openDetail = async (id: number) => {
    try {
      const lead = await api.getLead(id);
      setActive(lead);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "加载详情失败");
    }
  };

  return (
    <div className="lead-panel">
      <div className="lead-toolbar">
        <h2>我的案源</h2>
        <button type="button" className="btn-ghost" onClick={refresh}>
          刷新
        </button>
      </div>
      {err && <p className="form-msg error">{err}</p>}
      {items.length === 0 ? (
        <p className="muted">暂无发布记录。可在「发案源」提交需求。</p>
      ) : (
        <ul className="lead-list">
          {items.map((l) => (
            <li key={l.id}>
              <button type="button" className="lead-card" onClick={() => void openDetail(l.id)}>
                <div className="lead-card-top">
                  <strong>{l.title}</strong>
                  <span className={`status-pill st-${l.status}`}>{l.status}</span>
                </div>
                <div className="lead-meta">
                  {l.scene} · {l.region} · {l.contact_masked}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      {active && (
        <div className="lead-detail">
          <h3>
            #{active.id} {active.title}
          </h3>
          <p>{active.summary}</p>
          <p className="muted">
            状态 {active.status}
            {active.virtual_number ? ` · 中间号 ${active.virtual_number}` : ""}
          </p>
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
