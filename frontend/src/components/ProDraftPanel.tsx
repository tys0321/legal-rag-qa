// 职业草稿：短表单 + RAG 生成 + 历史回看 + Word/PDF 导出 + 关联案件

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { DraftMode, MatterItem, OpinionResult } from "../api/types";
import { DRAFT_CONFIG } from "../data/proDraftConfig";
import ExportButtons from "./ExportButtons";
import MarkdownDoc from "./MarkdownDoc";
import SourceCard from "./SourceCard";
import WorkHistory from "./WorkHistory";

interface Props {
  mode: DraftMode;
  /** 外部灌入字段（如要件补侦提示） */
  seedValues?: Record<string, string>;
  seedScene?: string;
}

export default function ProDraftPanel({ mode, seedValues, seedScene }: Props) {
  const cfg = DRAFT_CONFIG[mode];
  const [scene, setScene] = useState(cfg.scenes[0] || "");
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<OpinionResult | null>(null);
  const [tick, setTick] = useState(0);
  const [activeRecordId, setActiveRecordId] = useState<number | null>(null);
  const [matters, setMatters] = useState<MatterItem[]>([]);
  const [matterId, setMatterId] = useState<number | "">("");
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const previewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const next = DRAFT_CONFIG[mode];
    const init: Record<string, string> = {};
    next.fields.forEach((f) => {
      init[f.key] = "";
    });
    setValues(init);
    setScene(next.scenes[0] || "");
    setResult(null);
    setErr("");
    setActiveRecordId(null);
    setMatterId("");
    api.listMatters(mode).then(setMatters).catch(() => setMatters([]));
  }, [mode]);

  useEffect(() => {
    if (!seedValues) return;
    setValues((prev) => ({ ...prev, ...seedValues }));
  }, [seedValues]);

  useEffect(() => {
    if (seedScene) setScene(seedScene);
  }, [seedScene]);

  const canSubmit = useMemo(() => {
    return cfg.fields
      .filter((f) => f.required)
      .every((f) => (values[f.key] || "").trim().length >= 4);
  }, [cfg.fields, values]);

  const showPreview = (row: OpinionResult, recordId?: number | null) => {
    setResult(row);
    setActiveRecordId(recordId ?? null);
    if (row.scene) setScene(row.scene);
    const open: Record<string, boolean> = {};
    cfg.sectionOrder.forEach((s, i) => {
      open[s.key] = i < 2;
    });
    setOpenSections(open);
    requestAnimationFrame(() => {
      previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    window.dispatchEvent(
      new CustomEvent("app:toast", {
        detail: { message: recordId ? "已打开历史草稿" : "草稿已生成", type: "success" },
      }),
    );
  };

  const generate = async () => {
    setBusy(true);
    setErr("");
    try {
      const parts = cfg.fields
        .map((f) => {
          const v = (values[f.key] || "").trim();
          return v ? `【${f.label}】\n${v}` : "";
        })
        .filter(Boolean);
      const question = (values[cfg.questionKey] || "").trim();
      const slot_answers: Record<string, string> = {};
      cfg.fields.forEach((f) => {
        const v = (values[f.key] || "").trim();
        if (v) slot_answers[f.label] = v;
      });
      const res = await api.generateOpinion({
        fact_summary: parts.join("\n\n"),
        scene,
        question,
        slot_answers,
        mode,
        matter_id: matterId === "" ? null : Number(matterId),
      });
      setTick((n) => n + 1);
      showPreview(res, res.record_id ?? null);
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
        new CustomEvent("app:toast", { detail: { message: "已复制", type: "success" } }),
      );
    } catch {
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "复制失败", type: "error" } }),
      );
    }
  };

  const fullFields = cfg.fields.filter((f) => !f.column || f.column === "full");
  const leftFields = cfg.fields.filter((f) => f.column === "left");
  const rightFields = cfg.fields.filter((f) => f.column === "right");
  const defaultFields = cfg.layout === "pleadings" ? [] : cfg.fields;

  const renderField = (f: (typeof cfg.fields)[0]) => (
    <label key={f.key}>
      {f.label}
      <textarea
        value={values[f.key] || ""}
        onChange={(e) => setValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
        rows={f.rows || 3}
        placeholder={f.placeholder}
      />
    </label>
  );

  return (
    <div className="lead-panel opinion-panel">
      <h2>{cfg.title}</h2>
      <p className="muted">{cfg.blurb}</p>

      <WorkHistory
        kind="opinion"
        tick={tick}
        activeId={activeRecordId}
        onOpen={(payload, meta) => showPreview(payload as unknown as OpinionResult, meta.id)}
      />

      {result && (
        <div
          ref={previewRef}
          className={`opinion-result template-history-preview ${result.blocked ? "blocked" : ""}`}
        >
          <div className="opinion-watermark">{result.watermark}</div>
          <div className="lead-meta">
            {result.title || cfg.title}
            {" · "}风险 {result.risk_level} · 置信度 {result.confidence}
            {result.blocked ? " · 已拦截" : ""}
            {activeRecordId ? " · 历史记录" : " · 刚生成"}
          </div>
          {cfg.sectionOrder.some((sec) => !!(result.sections?.[sec.key] || "").trim()) ? (
            <div className="section-fold-list">
              {cfg.sectionOrder.map((sec) => {
                const body = result.sections?.[sec.key] || "";
                if (!body.trim()) return null;
                const open = openSections[sec.key] !== false;
                return (
                  <details
                    key={sec.key}
                    className="section-fold"
                    open={open}
                    onToggle={(e) =>
                      setOpenSections((prev) => ({
                        ...prev,
                        [sec.key]: (e.target as HTMLDetailsElement).open,
                      }))
                    }
                  >
                    <summary>{sec.label}</summary>
                    <MarkdownDoc markdown={body} className="template-preview-doc" />
                  </details>
                );
              })}
            </div>
          ) : (
            <MarkdownDoc markdown={result.markdown} className="template-preview-doc" />
          )}
          <SourceCard sources={result.sources || []} title="引用" />
          <div className="btn-row">
            <button type="button" className="btn-gold" onClick={() => void copyMd()}>
              复制全文
            </button>
            {!result.blocked && (
              <ExportButtons title={result.title || cfg.title} markdown={result.markdown || ""} />
            )}
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setResult(null);
                setActiveRecordId(null);
              }}
            >
              关闭预览
            </button>
          </div>
        </div>
      )}

      <div className="lawyer-form">
        <label>
          {cfg.sceneLabel}
          <select value={scene} onChange={(e) => setScene(e.target.value)}>
            {cfg.scenes.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
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

        {cfg.layout === "pleadings" ? (
          <>
            {fullFields.map(renderField)}
            <div className="pleadings-grid">
              <div className="pleadings-col">{leftFields.map(renderField)}</div>
              <div className="pleadings-col">{rightFields.map(renderField)}</div>
            </div>
          </>
        ) : (
          defaultFields.map(renderField)
        )}

        <button
          className="btn-primary"
          type="button"
          disabled={busy || !canSubmit}
          onClick={() => void generate()}
        >
          {busy ? "生成中…" : cfg.button}
        </button>
        {err && <p className="form-msg error">{err}</p>}
      </div>
    </div>
  );
}
