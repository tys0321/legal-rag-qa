// 合同审查：条款级批注 + 关联案件

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractFinding, ContractReviewResult, MatterItem } from "../api/types";
import WorkHistory from "./WorkHistory";
import ExportButtons from "./ExportButtons";
import SourceCard from "./SourceCard";

function asFinding(f: string | ContractFinding): ContractFinding {
  if (typeof f === "string") {
    return { clause: "未标明条款", risk: f, suggestion: "", severity: "中" };
  }
  return {
    clause: f.clause || "未标明条款",
    risk: f.risk || "",
    suggestion: f.suggestion || "",
    severity: f.severity || "中",
  };
}

export default function ContractReviewPanel() {
  const [title, setTitle] = useState("");
  const [focus, setFocus] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<ContractReviewResult | null>(null);
  const [tick, setTick] = useState(0);
  const [matters, setMatters] = useState<MatterItem[]>([]);
  const [matterId, setMatterId] = useState<number | "">("");

  useEffect(() => {
    api.listMatters("lawyer").then(setMatters).catch(() => setMatters([]));
  }, []);

  const submit = async () => {
    setBusy(true);
    setErr("");
    try {
      setResult(
        await api.contractReview({
          title,
          text,
          focus,
          matter_id: matterId === "" ? null : Number(matterId),
        }),
      );
      setTick((n) => n + 1);
    } catch (e) {
      setResult(null);
      setErr(e instanceof Error ? e.message : "审查失败");
    } finally {
      setBusy(false);
    }
  };

  const findings = (result?.findings || []).map(asFinding);

  return (
    <div className="lead-panel contract-panel">
      <h2>合同审查</h2>
      <p className="muted">粘贴合同摘录，生成条款级风险批注、法规对照和审查备忘录草稿。须律师审核后再使用。</p>
      <WorkHistory
        kind="contract"
        tick={tick}
        onOpen={(payload) => {
          const row = payload as unknown as ContractReviewResult;
          setResult(row);
          if (row.title) setTitle(row.title);
          if (row.focus) setFocus(row.focus);
          requestAnimationFrame(() => {
            document.querySelector(".opinion-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
          });
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
          关联案件（可选）
          <select
            value={matterId === "" ? "" : String(matterId)}
            onChange={(e) => setMatterId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">不关联</option>
            {matters.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
              </option>
            ))}
          </select>
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
          {findings.length > 0 && (
            <section className="opinion-section">
              <h3>条款批注</h3>
              <ul className="clause-findings">
                {findings.map((f, i) => (
                  <li key={`${f.clause}-${i}`} className={`clause-card sev-${f.severity}`}>
                    <div className="clause-card-top">
                      <strong>{f.clause}</strong>
                      <span className={`src-tag sev-tag-${f.severity}`}>{f.severity}</span>
                    </div>
                    <p>
                      <em>风险：</em>
                      {f.risk}
                    </p>
                    {f.suggestion && (
                      <p>
                        <em>建议：</em>
                        {f.suggestion}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <SourceCard sources={result.sources || []} title="对照材料" />
          {result.disclaimer && <p className="muted">{result.disclaimer}</p>}
          <ExportButtons
            title={result.title || "合同审查"}
            markdown={
              result.markdown ||
              findings.map((f) => `- 【${f.clause}】${f.risk}`).join("\n")
            }
          />
        </div>
      )}
    </div>
  );
}
