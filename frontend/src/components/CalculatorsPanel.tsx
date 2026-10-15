// 法律计算器 ×5：选类型 → 填参数 → 查看估算结果

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { CalculatorDetail, CalculatorRunResult, CalculatorSummary } from "../api/types";

export default function CalculatorsPanel() {
  const [items, setItems] = useState<CalculatorSummary[]>([]);
  const [notice, setNotice] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<CalculatorDetail | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<CalculatorRunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listCalculators()
      .then((res) => {
        setItems(res.items);
        setNotice(res.notice);
        if (res.items[0]) setSelectedId(res.items[0].id);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setBusy(true);
    setErr("");
    setResult(null);
    api
      .getCalculator(selectedId)
      .then((d) => {
        setDetail(d);
        const init: Record<string, string> = {};
        d.fields.forEach((f) => {
          init[f.key] = f.placeholder && f.type === "select" ? f.placeholder : "";
        });
        setValues(init);
      })
      .catch((e) => {
        setDetail(null);
        setErr(e instanceof Error ? e.message : "加载计算器失败");
      })
      .finally(() => setBusy(false));
  }, [selectedId]);

  const canRun = useMemo(() => {
    if (!detail) return false;
    return detail.fields
      .filter((f) => f.required)
      .every((f) => (values[f.key] || "").trim().length > 0);
  }, [detail, values]);

  const run = async () => {
    if (!selectedId) return;
    setBusy(true);
    setErr("");
    try {
      const inputs: Record<string, string | number> = {};
      for (const [k, v] of Object.entries(values)) {
        const field = detail?.fields.find((f) => f.key === k);
        if (field?.type === "number" && v.trim() !== "") {
          inputs[k] = Number(v);
        } else {
          inputs[k] = v;
        }
      }
      const res = await api.runCalculator(selectedId, inputs);
      setResult(res);
    } catch (e) {
      setResult(null);
      setErr(e instanceof Error ? e.message : "计算失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-panel calculators-panel">
      <h2>法律计算器</h2>
      <p className="muted">
        首批 5 类：诉讼费、民间借贷利息、工伤简版、交通事故医疗费、加班费。结果区强制标注估算仅供参考。
      </p>

      <div className="template-picker">
        {items.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`template-chip ${selectedId === c.id ? "active" : ""}`}
            onClick={() => setSelectedId(c.id)}
          >
            <span className="template-chip-name">{c.name}</span>
            <span className="template-chip-cat">{c.category}</span>
          </button>
        ))}
      </div>

      {detail && (
        <div className="lawyer-form">
          <p className="muted">{detail.description}</p>
          {detail.fields.map((f) => (
            <label key={f.key}>
              {f.label}
              {f.required ? " *" : ""}
              {f.type === "select" ? (
                <select
                  value={values[f.key] || f.options[0] || ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                >
                  {(f.options.length ? f.options : ["否", "是"]).map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.type === "number" ? "number" : "text"}
                  value={values[f.key] || ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  placeholder={f.placeholder || ""}
                  step="any"
                  min={0}
                />
              )}
            </label>
          ))}
          <button className="btn-primary" type="button" disabled={busy || !canRun} onClick={() => void run()}>
            {busy ? "计算中…" : "开始估算"}
          </button>
          {err && <p className="form-msg error">{err}</p>}
        </div>
      )}

      {result && (
        <div className="opinion-result calc-result">
          <div className="opinion-watermark">{result.notice || notice || "估算仅供参考"}</div>
          <div className="lead-meta">
            {result.name}
            {result.category ? ` · ${result.category}` : ""}
          </div>
          <div className="calc-total">
            <span className="calc-total-label">估算合计</span>
            <span className="calc-total-value">
              ¥ {result.total.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          {result.formula && <p className="muted calc-formula">公式：{result.formula}</p>}
          <ul className="event-list calc-lines">
            {result.lines.map((line, i) => (
              <li key={`${line.label}-${i}`}>
                <span className="event-type">{line.label}</span>
                <span>{line.value}</span>
              </li>
            ))}
          </ul>
          {result.warnings?.length > 0 && (
            <ul className="calc-warnings">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
