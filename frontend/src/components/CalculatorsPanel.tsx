// 法律计算器 ×5：选类型 → 填参数 → 查看估算结果

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  CalculatorDetail,
  CalculatorRunResult,
  CalculatorSummary,
  MatterItem,
} from "../api/types";
import WorkHistory from "./WorkHistory";
import ExportButtons from "./ExportButtons";

interface Props {
  audience?: string;
  title?: string;
  roleMode?: "lawyer" | "judge" | "prosecutor";
}

export default function CalculatorsPanel({ audience, title, roleMode }: Props) {
  const [items, setItems] = useState<CalculatorSummary[]>([]);
  const [notice, setNotice] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<CalculatorDetail | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<CalculatorRunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [tick, setTick] = useState(0);
  const [matters, setMatters] = useState<MatterItem[]>([]);
  const [matterId, setMatterId] = useState<number | "">("");
  const [dueDate, setDueDate] = useState("");

  useEffect(() => {
    api
      .listCalculators(audience)
      .then((res) => {
        setItems(res.items);
        setNotice(res.notice);
        setSelectedId(res.items[0]?.id || "");
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, [audience]);

  useEffect(() => {
    if (!roleMode) return;
    api.listMatters(roleMode).then(setMatters).catch(() => setMatters([]));
  }, [roleMode]);

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
      setTick((n) => n + 1);
    } catch (e) {
      setResult(null);
      setErr(e instanceof Error ? e.message : "计算失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lead-panel calculators-panel">
      <h2>{title || "法律计算器"}</h2>
      <p className="muted">
        选类型并填完带 * 的参数后点「开始估算」。结果仅为估算，供参考。
      </p>
      {err && <p className="form-msg error">{err}</p>}
      <WorkHistory
        kind="calculator"
        tick={tick}
        onOpen={(payload) => {
          setResult(payload as unknown as CalculatorRunResult);
          requestAnimationFrame(() => {
            document.querySelector(".opinion-result, .calc-result")?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          });
        }}
      />

      {items.length === 0 && !err ? (
        <p className="muted">{busy ? "计算器加载中…" : "暂无可用计算器"}</p>
      ) : (
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
      )}

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
          {!canRun && !busy && (
            <p className="muted">请先填完所有带 * 的必填项，按钮才会可点。</p>
          )}
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
              ¥{" "}
              {Number(result.total ?? 0).toLocaleString("zh-CN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
          </div>
          {result.formula && <p className="muted calc-formula">公式：{result.formula}</p>}
          <ul className="event-list calc-lines">
            {(result.lines || []).map((line, i) => (
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
          {roleMode && (
            <div className="matter-inline-form calc-matter-bind">
              <select
                value={matterId === "" ? "" : String(matterId)}
                onChange={(e) => setMatterId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">写入案件期限…</option>
                {matters.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}
                  </option>
                ))}
              </select>
              <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              <button
                type="button"
                className="btn-gold"
                disabled={matterId === "" || busy}
                onClick={async () => {
                  if (matterId === "") return;
                  try {
                    await api.addMatterDeadline(Number(matterId), {
                      label: `${result.name}（估算 ¥${Number(result.total).toFixed(2)}）`,
                      due_date: dueDate || null,
                      calc_key: result.id,
                    });
                    window.dispatchEvent(
                      new CustomEvent("app:toast", {
                        detail: { message: "已写入案件期限", type: "success" },
                      }),
                    );
                  } catch (e) {
                    window.dispatchEvent(
                      new CustomEvent("app:toast", {
                        detail: {
                          message: e instanceof Error ? e.message : "写入失败",
                          type: "error",
                        },
                      }),
                    );
                  }
                }}
              >
                写入期限
              </button>
            </div>
          )}
          <ExportButtons
            title={result.name || "计算估算"}
            markdown={[
              `# ${result.name}`,
              "",
              `估算合计：¥ ${result.total.toFixed(2)}`,
              result.formula ? `公式：${result.formula}` : "",
              "",
              ...result.lines.map((line) => `- ${line.label}：${line.value}`),
              "",
              result.notice || notice || "估算仅供参考",
            ].join("\n")}
          />
        </div>
      )}
    </div>
  );
}
