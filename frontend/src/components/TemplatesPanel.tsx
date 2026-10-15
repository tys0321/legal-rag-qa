// 文书模板 ×8：选模板 → 填槽位 → 复制 Markdown

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { TemplateDetail, TemplateFillResult, TemplateSummary } from "../api/types";

export default function TemplatesPanel() {
  const [items, setItems] = useState<TemplateSummary[]>([]);
  const [watermark, setWatermark] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<TemplateFillResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listTemplates()
      .then((res) => {
        setItems(res.items);
        setWatermark(res.watermark);
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
      .getTemplate(selectedId)
      .then((d) => {
        setDetail(d);
        const init: Record<string, string> = {};
        d.fields.forEach((f) => {
          init[f.key] = "";
        });
        setValues(init);
      })
      .catch((e) => {
        setDetail(null);
        setErr(e instanceof Error ? e.message : "加载模板失败");
      })
      .finally(() => setBusy(false));
  }, [selectedId]);

  const canGenerate = useMemo(() => {
    if (!detail) return false;
    return detail.fields
      .filter((f) => f.required)
      .every((f) => (values[f.key] || "").trim().length > 0);
  }, [detail, values]);

  const generate = async () => {
    if (!selectedId) return;
    setBusy(true);
    setErr("");
    try {
      const res = await api.fillTemplate(selectedId, values);
      setResult(res);
      if (res.missing_required?.length) {
        window.dispatchEvent(
          new CustomEvent("app:toast", {
            detail: { message: `仍有必填项未填：${res.missing_required.join(", ")}`, type: "warn" },
          }),
        );
      }
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
    <div className="lead-panel templates-panel">
      <h2>文书模板</h2>
      <p className="muted">
        首批 8 种常用文书：表单填槽后生成可复制 Markdown。水印：{watermark || "AI 生成草稿，须律师审核"}。
      </p>

      <div className="template-picker">
        {items.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`template-chip ${selectedId === t.id ? "active" : ""}`}
            onClick={() => setSelectedId(t.id)}
          >
            <span className="template-chip-name">{t.name}</span>
            <span className="template-chip-cat">{t.category}</span>
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
              {f.type === "textarea" ? (
                <textarea
                  value={values[f.key] || ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  rows={3}
                  placeholder={f.placeholder || ""}
                />
              ) : (
                <input
                  value={values[f.key] || ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  placeholder={f.placeholder || ""}
                />
              )}
            </label>
          ))}
          <button
            className="btn-primary"
            type="button"
            disabled={busy || !canGenerate}
            onClick={() => void generate()}
          >
            {busy ? "生成中…" : "生成文书草稿"}
          </button>
          {err && <p className="form-msg error">{err}</p>}
        </div>
      )}

      {result && (
        <div className="opinion-result">
          <div className="opinion-watermark">{result.watermark}</div>
          <div className="lead-meta">
            {result.name}
            {result.category ? ` · ${result.category}` : ""}
          </div>
          <pre className="template-preview">{result.markdown}</pre>
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
