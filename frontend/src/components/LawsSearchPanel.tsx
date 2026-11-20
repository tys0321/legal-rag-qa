// 法规检索页：调用混合检索（BM25 + 向量 + 重排）

import { useState } from "react";
import { api } from "../api/client";
import type { LawHit } from "../api/types";
import SourceCard from "./SourceCard";

export default function LawsSearchPanel() {
  const [q, setQ] = useState("劳动合同 拖欠工资");
  const [items, setItems] = useState<LawHit[]>([]);
  const [backend, setBackend] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const search = async () => {
    const query = q.trim();
    if (!query) return;
    setBusy(true);
    setErr("");
    try {
      const res = await api.searchLaws(query, 10);
      setItems(res.items);
      setBackend(res.backend);
    } catch (e) {
      setItems([]);
      setErr(e instanceof Error ? e.message : "检索失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-panel laws-panel">
      <h2>法规检索</h2>
      <p className="muted">
        使用与问答相同的<strong>混合检索</strong>链路（BM25 + 稠密向量 + 条款精确 + 重排），结果含效力状态与条款定位。
      </p>
      <div className="laws-search-bar">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="输入法条关键词或问题，如：劳动合同法 第三十条"
          onKeyDown={(e) => {
            if (e.key === "Enter") void search();
          }}
        />
        <button className="btn-primary" type="button" disabled={busy || !q.trim()} onClick={() => void search()}>
          {busy ? "检索中…" : "检索"}
        </button>
      </div>
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
          article: hit.article,
          text: hit.text,
          category: hit.category,
          score: hit.score,
          match: hit.match,
          effective_status: hit.effective_status,
          effective_detail: hit.effective_detail,
          page: hit.page,
        }))}
        title="检索结果"
      />
      {!busy && items.length === 0 && !err && <p className="muted">输入关键词后点击检索。</p>}
    </div>
  );
}
