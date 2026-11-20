// 检察官：罪名构成要件勾选 → 补侦要点（分组 + 证据提示）

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { ElementsCheckResult, MatterItem } from "../api/types";

type ChargeSummary = {
  key: string;
  charge: string;
  category: string;
  article_hint: string;
  element_count: number;
};

type ElementRow = {
  id: string;
  label: string;
  desc: string;
  group?: string;
  evidence?: string;
};

interface Props {
  onFillDraft?: (text: string, charge: string) => void;
}

export default function ElementsChecklist({ onFillDraft }: Props) {
  const [charges, setCharges] = useState<ChargeSummary[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState("全部");
  const [q, setQ] = useState("");
  const [chargeKey, setChargeKey] = useState("盗窃");
  const [elements, setElements] = useState<ElementRow[]>([]);
  const [groups, setGroups] = useState<Array<{ group: string; items: ElementRow[] }>>([]);
  const [hint, setHint] = useState("");
  const [compare, setCompare] = useState<string[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ElementsCheckResult | null>(null);
  const [matters, setMatters] = useState<MatterItem[]>([]);
  const [matterId, setMatterId] = useState<number | "">("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listElementCharges()
      .then((r: any) => {
        const items: ChargeSummary[] = (r.items || []).map((it: any) =>
          typeof it === "string"
            ? { key: it, charge: it, category: "其他", article_hint: "", element_count: 0 }
            : it,
        );
        setCharges(items);
        setCategories(["全部", ...(r.categories || [])]);
        if (items[0]) setChargeKey(items[0].key);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载罪名失败"));
    api.listMatters("prosecutor").then(setMatters).catch(() => undefined);
  }, []);

  const filteredCharges = useMemo(() => {
    const kw = q.trim();
    return charges.filter((c) => {
      if (category !== "全部" && c.category !== category) return false;
      if (!kw) return true;
      return c.charge.includes(kw) || c.key.includes(kw) || (c.article_hint || "").includes(kw);
    });
  }, [charges, category, q]);

  useEffect(() => {
    if (!chargeKey) return;
    setBusy(true);
    api
      .getChargeElements(chargeKey)
      .then((r: any) => {
        setElements(r.elements || []);
        setGroups(r.groups || []);
        setHint(r.article_hint || "");
        setCompare(r.compare || []);
        const init: Record<string, boolean> = {};
        (r.elements || []).forEach((e: ElementRow) => {
          init[e.id] = false;
        });
        setChecked(init);
        setNotes({});
        setResult(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载要件失败"))
      .finally(() => setBusy(false));
  }, [chargeKey]);

  const checkedCount = Object.values(checked).filter(Boolean).length;
  const totalCount = elements.length;

  const toggleGroup = (items: ElementRow[], on: boolean) => {
    setChecked((prev) => {
      const next = { ...prev };
      items.forEach((e) => {
        next[e.id] = on;
      });
      return next;
    });
  };

  const runCheck = async () => {
    setBusy(true);
    setErr("");
    try {
      const ids = Object.entries(checked)
        .filter(([, v]) => v)
        .map(([k]) => k);
      const notePayload: Record<string, string> = {};
      Object.entries(notes).forEach(([k, v]) => {
        if (v.trim()) notePayload[k] = v.trim();
      });
      const res = await api.checkElements({
        charge: chargeKey,
        checked_ids: ids,
        notes: notePayload,
        matter_id: matterId === "" ? null : Number(matterId),
      });
      setResult(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "勾选失败");
    } finally {
      setBusy(false);
    }
  };

  const displayGroups =
    groups.length > 0
      ? groups
      : [{ group: "构成要件", items: elements }];

  return (
    <div className="lead-panel elements-panel">
      <h2>构成要件勾选</h2>
      <p className="muted">
        按「构成要件 / 证据要点 / 程序审查」对照勾选已有证据支撑项，生成带调取建议的补侦提纲；可写入案件或填入审查报告。
        当前库已收录 <strong>{charges.length}</strong> 个常见罪名/案由。
      </p>
      {err && <p className="form-msg error">{err}</p>}

      <div className="lawyer-form">
        <div className="matter-inline-form">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索罪名 / 法条"
          />
        </div>

        <label>
          罪名（{filteredCharges.length}）
          <select value={chargeKey} onChange={(e) => setChargeKey(e.target.value)}>
            {filteredCharges.map((c) => (
              <option key={c.key} value={c.key}>
                {c.category ? `【${c.category}】` : ""}
                {c.charge}
                {c.element_count ? ` · ${c.element_count}项` : ""}
              </option>
            ))}
          </select>
        </label>
        {hint && <p className="muted">{hint}</p>}
        {compare.length > 0 && (
          <p className="elements-compare">
            此罪彼罪注意：{compare.join("、")}
          </p>
        )}

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

        <div className="elements-progress muted">
          已勾选 {checkedCount} / {totalCount}
          <button
            type="button"
            className="btn-ghost"
            onClick={() =>
              setChecked(Object.fromEntries(elements.map((e) => [e.id, true])))
            }
          >
            全选
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() =>
              setChecked(Object.fromEntries(elements.map((e) => [e.id, false])))
            }
          >
            清空
          </button>
        </div>

        {displayGroups.map((g) => (
          <div key={g.group} className="elements-group">
            <div className="elements-group-head">
              <strong>{g.group}</strong>
              <span className="muted">
                {g.items.filter((e) => checked[e.id]).length}/{g.items.length}
              </span>
              <button type="button" className="btn-ghost" onClick={() => toggleGroup(g.items, true)}>
                本组全选
              </button>
              <button type="button" className="btn-ghost" onClick={() => toggleGroup(g.items, false)}>
                清空
              </button>
            </div>
            <div className="elements-checklist">
              {g.items.map((el) => (
                <div key={el.id} className={`element-item ${checked[el.id] ? "on" : ""}`}>
                  <label className="element-main">
                    <input
                      type="checkbox"
                      checked={!!checked[el.id]}
                      onChange={(e) =>
                        setChecked((prev) => ({ ...prev, [el.id]: e.target.checked }))
                      }
                    />
                    <span>
                      <strong>{el.label}</strong>
                      <span className="muted"> — {el.desc}</span>
                    </span>
                  </label>
                  {el.evidence && (
                    <p className="element-evidence">建议证据：{el.evidence}</p>
                  )}
                  <input
                    className="element-note"
                    value={notes[el.id] || ""}
                    onChange={(e) =>
                      setNotes((prev) => ({ ...prev, [el.id]: e.target.value }))
                    }
                    placeholder="承办备注（可选）：已有证据/缺口说明"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}

        <button className="btn-primary" type="button" disabled={busy} onClick={() => void runCheck()}>
          {busy ? "生成中…" : "生成补侦要点"}
        </button>
      </div>

      {result && (
        <div className="opinion-result">
          <div className="lead-meta">
            {result.charge}
            {result.article_hint ? ` · ${result.article_hint}` : ""}
            {` · 缺 ${result.missing.length} 项`}
          </div>
          <pre className="matter-extract-preview">{result.supplement_text}</pre>
          <div className="btn-row">
            {onFillDraft && (
              <button
                type="button"
                className="btn-gold"
                onClick={() => onFillDraft(result.supplement_text, result.charge)}
              >
                填入审查报告
              </button>
            )}
            <button
              type="button"
              className="btn-ghost"
              onClick={async () => {
                await navigator.clipboard.writeText(result.supplement_text);
                window.dispatchEvent(
                  new CustomEvent("app:toast", { detail: { message: "已复制", type: "success" } }),
                );
              }}
            >
              复制
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
