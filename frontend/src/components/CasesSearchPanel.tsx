// 类案卡：司法解释 / 批复 / 指导性文件（向量检索）

import { useState } from "react";
import { api } from "../api/client";
import type { CaseHit } from "../api/types";

const KIND_LABEL: Record<string, string> = {
  judicial_interp: "司法解释",
  guiding_case: "指导案例/公报",
  reply: "批复/答复",
  decision: "决定",
  reference: "参考材料",
};

export default function CasesSearchPanel() {
  const [q, setQ] = useState("劳动争议 拖欠工资");
  const [items, setItems] = useState<CaseHit[]>([]);
  const [notice, setNotice] = useState("");
  const [backend, setBackend] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const search = async () => {
    const query = q.trim();
    if (!query) return;
    setBusy(true);
    setErr("");
    try {
      const res = await api.searchCases(query, 8);
      setItems(res.items);
      setNotice(res.notice || "");
      setBackend(res.backend);
      setExpanded(res.items[0]?.id ?? null);
    } catch (e) {
      setItems([]);
      setErr(e instanceof Error ? e.message : "检索失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-panel cases-panel">
      <h2>类案参考</h2>
      <p className="muted">
        基于<strong>稠密向量检索</strong>，筛选司法解释、批复、指导性文件等案例特征文档。
      </p>
      <div className="laws-search-bar">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="输入案情关键词，如：劳动争议 加班费"
          onKeyDown={(e) => {
            if (e.key === "Enter") void search();
          }}
        />
        <button className="btn-primary" type="button" disabled={busy || !q.trim()} onClick={() => void search()}>
          {busy ? "检索中…" : "检索类案"}
        </button>
      </div>
      {notice && <div className="risk-banner warn inline">{notice}</div>}
      {backend && (
        <p className="muted">
          引擎：{backend} · 命中 {items.length} 条
        </p>
      )}
      {err && <p className="form-msg error">{err}</p>}

      <ul className="lead-list case-cards">
        {items.map((hit) => (
          <li key={hit.id}>
            <button
              type="button"
              className="lead-card case-card"
              onClick={() => setExpanded(expanded === hit.id ? null : hit.id)}
            >
              <div className="lead-card-top">
                <strong>{hit.title}</strong>
                <span className="match-score">{hit.score.toFixed(3)}</span>
              </div>
              <div className="lead-meta">
                <span className="status-pill">{KIND_LABEL[hit.kind] || hit.kind}</span>
                {hit.category ? ` · ${hit.category}` : ""}
              </div>
              {expanded === hit.id && (
                <p className="lead-summary law-excerpt">
                  {(hit.text || "").slice(0, 600)}
                  {(hit.text || "").length > 600 ? "…" : ""}
                </p>
              )}
            </button>
          </li>
        ))}
      </ul>
      {!busy && items.length === 0 && !err && <p className="muted">输入关键词后检索类案参考材料。</p>}
      {!busy && items.length === 0 && !err && backend && (
        <p className="muted">暂无命中：可入库「司法解释 / 批复 / 指导案例」类文档后再试。</p>
      )}
    </div>
  );
}
