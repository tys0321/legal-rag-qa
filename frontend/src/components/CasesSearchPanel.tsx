// 类案卡：司法解释 / 批复 / 指导性文件（向量检索）

import { useState } from "react";
import { api } from "../api/client";
import type { CaseHit } from "../api/types";
import SourceCard from "./SourceCard";

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

      <SourceCard
        sources={items.map((hit) => ({
          id: hit.id,
          title: hit.title,
          text: hit.text,
          category: `${KIND_LABEL[hit.kind] || hit.kind}${hit.category ? ` · ${hit.category}` : ""}`,
          score: hit.score,
        }))}
        title="类案命中"
      />
      {!busy && items.length === 0 && !err && <p className="muted">输入关键词后检索类案参考材料。</p>}
      {!busy && items.length === 0 && !err && backend && (
        <p className="muted">暂无命中：可入库「司法解释 / 批复 / 指导案例」类文档后再试。</p>
      )}
    </div>
  );
}
