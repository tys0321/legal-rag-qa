// 合同审查：粘贴摘录 → 风险点 + 法规对照 + 备忘录草稿

import { useState } from "react";
import { api } from "../api/client";
import type { ContractReviewResult } from "../api/types";
import WorkHistory from "./WorkHistory";
import ExportButtons from "./ExportButtons";

export default function ContractReviewPanel() {
  const [title, setTitle] = useState("");
  const [focus, setFocus] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<ContractReviewResult | null>(null);
  const [tick, setTick] = useState(0);

  const submit = async () => {
    setBusy(true);
    setErr("");
    try {
      setResult(await api.contractReview({ title, text, focus }));
      setTick((n) => n + 1);
    } catch (e) {
      setResult(null);
      setErr(e instanceof Error ? e.message : "审查失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-panel contract-panel">
      <h2>合同审查</h2>
      <p className="muted">粘贴合同摘录，生成风险点、法规对照和审查备忘录草稿。须律师审核后再使用。</p>
      <WorkHistory
        kind="contract"
        tick={tick}
        onOpen={(payload) => {
          const row = payload as unknown as ContractReviewResult;
          setResult(row);
          if (row.title) setTitle(row.title);
          if (row.focus) setFocus(row.focus);
        }}
      />
      <div className="lawyer-form">
        <label>
          合同标题
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：房屋租赁合同" />
        </label>
        <label>
          关注点（可选）
          <input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="如：违约金、解除、管辖" />
        </label>
        <label>
          合同正文摘录
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="粘贴需要审查的条款"
          />
        </label>
        <button className="btn-primary" type="button" disabled={busy || text.trim().length < 4} onClick={() => void submit()}>
          {busy ? "审查中…" : "提交审查"}
        </button>
        {err && <p className="form-msg error">{err}</p>}
      </div>
      {result && (
        <div className="opinion-result">
          <div className="opinion-watermark">{result.watermark}</div>
          <p className="law-excerpt">{result.message}</p>
          {result.findings.length > 0 && (
            <section className="opinion-section">
              <h3>风险点</h3>
              <ul className="event-list">
                {result.findings.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </section>
          )}
          {result.sources.length > 0 && (
            <section className="opinion-section">
              <h3>对照材料</h3>
              <ul className="event-list">
                {result.sources.map((s, i) => (
                  <li key={s.id || i}>
                    [{i + 1}] {s.title}
                    {s.article ? ` ${s.article}` : ""}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {result.disclaimer && <p className="muted">{result.disclaimer}</p>}
          <ExportButtons title={result.title || "合同审查"} markdown={result.markdown || result.findings.join("\n")} />
        </div>
      )}
    </div>
  );
}
