// 法律意见书：案情 → RAG+LLM 结构化草稿

import { useState } from "react";
import { api } from "../api/client";
import type { OpinionResult } from "../api/types";

const SCENES = [
  "劳动用工",
  "房屋租赁",
  "婚姻家事",
  "交通事故",
  "消费维权",
  "行政诉讼",
  "合同纠纷",
];

export default function OpinionPanel() {
  const [scene, setScene] = useState("劳动用工");
  const [question, setQuestion] = useState("如何依法维权");
  const [fact, setFact] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<OpinionResult | null>(null);

  const generate = async () => {
    setBusy(true);
    setErr("");
    try {
      const res = await api.generateOpinion({
        fact_summary: fact,
        scene,
        question,
      });
      setResult(res);
    } catch (e) {
      setResult(null);
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      setBusy(false);
    }
  };

  const copyMd = async () => {
    if (!result?.markdown) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "已复制 Markdown", type: "success" } }),
      );
    } catch {
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "复制失败", type: "error" } }),
      );
    }
  };

  return (
    <div className="lead-panel opinion-panel">
      <h2>法律意见书</h2>
      <p className="muted">
        基于<strong>混合检索 + LLM</strong>生成结构化草稿（案情梳理 → 法律分析 → 行动建议 → 免责声明）。
      </p>
      <div className="lawyer-form">
        <label>
          场景
          <select value={scene} onChange={(e) => setScene(e.target.value)}>
            {SCENES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          核心诉求
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="如：如何追讨拖欠工资" />
        </label>
        <label>
          案情摘要
          <textarea
            value={fact}
            onChange={(e) => setFact(e.target.value)}
            rows={5}
            placeholder="简述事实经过、证据与诉求（勿填写敏感证件号）"
          />
        </label>
        <button
          className="btn-primary"
          type="button"
          disabled={busy || fact.trim().length < 4}
          onClick={() => void generate()}
        >
          {busy ? "生成中…" : "生成意见书草稿"}
        </button>
        {err && <p className="form-msg error">{err}</p>}
      </div>

      {result && (
        <div className={`opinion-result ${result.blocked ? "blocked" : ""}`}>
          <div className="opinion-watermark">{result.watermark}</div>
          <div className="lead-meta">
            风险 {result.risk_level} · 置信度 {result.confidence}
            {result.blocked ? " · 已拦截" : ""}
          </div>
          {(["case_summary", "legal_analysis", "action_advice", "disclaimer"] as const).map((key) => {
            const titles: Record<string, string> = {
              case_summary: "案情梳理",
              legal_analysis: "法律分析",
              action_advice: "行动建议",
              disclaimer: "免责声明",
            };
            const body = result.sections[key];
            if (!body) return null;
            return (
              <section key={key} className="opinion-section">
                <h3>{titles[key]}</h3>
                <p className="law-excerpt">{body}</p>
              </section>
            );
          })}
          {result.sources?.length > 0 && (
            <section className="opinion-section">
              <h3>引用材料</h3>
              <ul className="event-list">
                {result.sources.map((s, i) => (
                  <li key={s.id || i}>
                    <span className="event-type">[{i + 1}]</span>
                    {s.title}
                    {s.article ? ` ${s.article}` : ""}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <div className="btn-row">
            <button type="button" className="btn-gold" onClick={() => void copyMd()}>
              复制 Markdown
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
