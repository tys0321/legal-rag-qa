// 文书模板：选模板 → 填槽位 → 预览 / 回看历史

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { TemplateDetail, TemplateFillResult, TemplateSummary } from "../api/types";
import WorkHistory from "./WorkHistory";
import ExportButtons from "./ExportButtons";
import MarkdownDoc from "./MarkdownDoc";
import { looksLikePhoneField, phoneError } from "../utils/validation";

interface Props {
  audience?: string;
  title?: string;
}

type FillPayload = TemplateFillResult & {
  filled_fields?: Record<string, string>;
};

export default function TemplatesPanel({ audience, title }: Props) {
  const [items, setItems] = useState<TemplateSummary[]>([]);
  const [watermark, setWatermark] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<FillPayload | null>(null);
  const [activeRecordId, setActiveRecordId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [fieldErrs, setFieldErrs] = useState<Record<string, string>>({});
  const [tick, setTick] = useState(0);
  const previewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .listTemplates(audience)
      .then((res) => {
        setItems(res.items);
        setWatermark(res.watermark);
        setSelectedId(res.items[0]?.id || "");
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, [audience]);

  useEffect(() => {
    if (!selectedId) return;
    setBusy(true);
    setErr("");
    api
      .getTemplate(selectedId)
      .then((d) => {
        setDetail(d);
        setValues((prev) => {
          const init: Record<string, string> = {};
          d.fields.forEach((f) => {
            init[f.key] = prev[f.key] || "";
          });
          return init;
        });
      })
      .catch((e) => {
        setDetail(null);
        setErr(e instanceof Error ? e.message : "加载模板失败");
      })
      .finally(() => setBusy(false));
  }, [selectedId]);

  const validateFields = (): boolean => {
    if (!detail) return false;
    const next: Record<string, string> = {};
    const junk = /^(没理由|无|测试|asdf|xxx+|地球|火星|123+|111+)$/i;

    for (const f of detail.fields) {
      const v = (values[f.key] || "").trim();
      if (f.required && v.length < 2) {
        next[f.key] = "请认真填写（至少 2 字）";
        continue;
      }
      if (f.required && junk.test(v)) {
        next[f.key] = "请勿填写无效占位内容";
        continue;
      }
      if (f.key.includes("address") && v && v.length < 4) {
        next[f.key] = "地址过短，请写到街道/门牌";
        continue;
      }
      if ((f.key.includes("facts") || f.key.includes("claims") || f.key === "claims") && v && v.length < 8) {
        next[f.key] = "请写具体一些（至少 8 字）";
        continue;
      }
      if (looksLikePhoneField(f.key, f.label) && v) {
        const pe = phoneError(v, false);
        if (pe) next[f.key] = pe;
      }
    }
    setFieldErrs(next);
    return Object.keys(next).length === 0;
  };

  const canGenerate = useMemo(() => {
    if (!detail) return false;
    return detail.fields
      .filter((f) => f.required)
      .every((f) => (values[f.key] || "").trim().length >= 2);
  }, [detail, values]);

  const showPreview = (payload: FillPayload, recordId: number | null = null) => {
    if (!payload?.markdown) {
      setErr("记录中没有可预览的文书内容");
      return;
    }
    setResult(payload);
    setActiveRecordId(recordId);
    if (payload.id) setSelectedId(String(payload.id));
    if (payload.filled_fields && typeof payload.filled_fields === "object") {
      setValues((prev) => ({ ...prev, ...payload.filled_fields }));
    }
    requestAnimationFrame(() => {
      previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const generate = async () => {
    if (!selectedId || !detail) return;
    if (!validateFields()) {
      setErr("请按提示修正标红字段后再生成");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const res = await api.fillTemplate(selectedId, values);
      const payload: FillPayload = { ...res, filled_fields: { ...values } };
      setResult(payload);
      setActiveRecordId(null);
      setTick((n) => n + 1);
      requestAnimationFrame(() => {
        previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
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
      <h2>{title || "文书模板"}</h2>
      <p className="muted">
        选模板并填完带 * 的必填项后，点「生成文书草稿」。水印：
        {watermark || "AI 生成草稿，须人工审核"}。手机号须为 11 位有效号码。
      </p>
      {err && <p className="form-msg error">{err}</p>}
      <WorkHistory
        kind="template"
        tick={tick}
        activeId={activeRecordId}
        onOpen={(payload, meta) => showPreview(payload as unknown as FillPayload, meta.id)}
      />

      {result?.markdown && (
        <div className="opinion-result template-history-preview" ref={previewRef}>
          <div className="opinion-watermark">{result.watermark || watermark}</div>
          <div className="lead-meta">
            {result.name || "文书草稿"}
            {result.category ? ` · ${result.category}` : ""}
            {activeRecordId ? " · 历史记录" : " · 刚生成"}
            · 预览
          </div>
          {result.missing_required && result.missing_required.length > 0 && (
            <p className="form-msg error">
              仍有未填项：{result.missing_required.join("、")}。请补全后重新生成。
            </p>
          )}
          <MarkdownDoc markdown={result.markdown} className="template-preview-doc" />
          <div className="btn-row">
            <button type="button" className="btn-gold" onClick={() => void copyMd()}>
              复制文本
            </button>
            <ExportButtons title={result.name || "文书草稿"} markdown={result.markdown} />
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

      {items.length === 0 && !err ? (
        <p className="muted">{busy ? "模板加载中…" : "暂无可用模板"}</p>
      ) : (
        <div className="template-picker">
          {items.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`template-chip ${selectedId === t.id ? "active" : ""}`}
              onClick={() => {
                setSelectedId(t.id);
                setResult(null);
                setActiveRecordId(null);
                setFieldErrs({});
              }}
            >
              <span className="template-chip-name">{t.name}</span>
              <span className="template-chip-cat">{t.category}</span>
            </button>
          ))}
        </div>
      )}

      {detail && (
        <div className="lawyer-form">
          <p className="muted">{detail.description}</p>
          {detail.fields.map((f) => (
            <label key={f.key}>
              {f.label}
              {f.required ? " *" : ""}
              {looksLikePhoneField(f.key, f.label) ? "（11 位手机号）" : ""}
              {f.type === "textarea" ? (
                <textarea
                  value={values[f.key] || ""}
                  onChange={(e) => {
                    setValues((v) => ({ ...v, [f.key]: e.target.value }));
                    setFieldErrs((fe) => {
                      const n = { ...fe };
                      delete n[f.key];
                      return n;
                    });
                  }}
                  rows={3}
                  placeholder={f.placeholder || ""}
                  className={fieldErrs[f.key] ? "input-invalid" : ""}
                />
              ) : (
                <input
                  value={values[f.key] || ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    const next = looksLikePhoneField(f.key, f.label)
                      ? raw.replace(/\D/g, "").slice(0, 11)
                      : raw;
                    setValues((v) => ({ ...v, [f.key]: next }));
                    setFieldErrs((fe) => {
                      const n = { ...fe };
                      delete n[f.key];
                      return n;
                    });
                  }}
                  placeholder={
                    looksLikePhoneField(f.key, f.label)
                      ? "如：13800138000"
                      : f.placeholder || ""
                  }
                  inputMode={looksLikePhoneField(f.key, f.label) ? "numeric" : undefined}
                  maxLength={looksLikePhoneField(f.key, f.label) ? 11 : undefined}
                  className={fieldErrs[f.key] ? "input-invalid" : ""}
                />
              )}
              {fieldErrs[f.key] && <span className="field-error">{fieldErrs[f.key]}</span>}
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
          {!canGenerate && !busy && (
            <p className="muted">请先填完所有带 * 的必填项，按钮才会可点。</p>
          )}
        </div>
      )}
    </div>
  );
}
