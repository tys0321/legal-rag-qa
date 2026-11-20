// 一案一档：案件列表 / 材料 / 期限 / 卷宗抽取

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { MatterArtifact, MatterDeadline, MatterItem } from "../api/types";

interface Props {
  roleMode: "lawyer" | "judge" | "prosecutor";
}

export default function CaseWorkspacePanel({ roleMode }: Props) {
  const [items, setItems] = useState<MatterItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [artifacts, setArtifacts] = useState<MatterArtifact[]>([]);
  const [deadlines, setDeadlines] = useState<MatterDeadline[]>([]);
  const [title, setTitle] = useState("");
  const [caseNo, setCaseNo] = useState("");
  const [cause, setCause] = useState("");
  const [noteTitle, setNoteTitle] = useState("办案备注");
  const [noteBody, setNoteBody] = useState("");
  const [dlLabel, setDlLabel] = useState("");
  const [dlDate, setDlDate] = useState("");
  const [extractText, setExtractText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const loadList = useCallback(async () => {
    try {
      const rows = await api.listMatters(roleMode);
      setItems(rows);
      if (selectedId && !rows.some((r) => r.id === selectedId)) {
        setSelectedId(rows[0]?.id ?? null);
      } else if (!selectedId && rows[0]) {
        setSelectedId(rows[0].id);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "加载案件失败");
    }
  }, [roleMode, selectedId]);

  const loadDetail = useCallback(async (id: number) => {
    try {
      const [arts, dls] = await Promise.all([
        api.listMatterArtifacts(id),
        api.listMatterDeadlines(id),
      ]);
      setArtifacts(arts);
      setDeadlines(dls);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "加载详情失败");
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [roleMode]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
    else {
      setArtifacts([]);
      setDeadlines([]);
    }
  }, [selectedId, loadDetail]);

  const create = async () => {
    if (!title.trim()) return;
    setBusy(true);
    setErr("");
    try {
      const row = await api.createMatter({
        title: title.trim(),
        case_no: caseNo.trim(),
        cause: cause.trim(),
        role_mode: roleMode,
      });
      setTitle("");
      setCaseNo("");
      setCause("");
      await loadList();
      setSelectedId(row.id);
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "案件已创建", type: "success" } }),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "创建失败");
    } finally {
      setBusy(false);
    }
  };

  const removeMatter = async (id: number) => {
    if (!confirm("确认删除该案件及其材料、期限？")) return;
    await api.deleteMatter(id);
    setSelectedId(null);
    await loadList();
  };

  const addNote = async () => {
    if (!selectedId || noteBody.trim().length < 2) return;
    setBusy(true);
    try {
      await api.addMatterArtifact(selectedId, {
        kind: "note",
        title: noteTitle || "办案备注",
        payload: { text: noteBody },
      });
      setNoteBody("");
      await loadDetail(selectedId);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "保存备注失败");
    } finally {
      setBusy(false);
    }
  };

  const addDeadline = async () => {
    if (!selectedId || !dlLabel.trim()) return;
    setBusy(true);
    try {
      await api.addMatterDeadline(selectedId, {
        label: dlLabel.trim(),
        due_date: dlDate || null,
      });
      setDlLabel("");
      setDlDate("");
      await loadDetail(selectedId);
      await loadList();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "添加期限失败");
    } finally {
      setBusy(false);
    }
  };

  const toggleDeadline = async (d: MatterDeadline) => {
    if (!selectedId) return;
    await api.updateMatterDeadline(selectedId, d.id, { done: !d.done });
    await loadDetail(selectedId);
    await loadList();
  };

  const runExtract = async () => {
    if (!selectedId) return;
    setBusy(true);
    setErr("");
    try {
      await api.extractMatterText(selectedId, { text: extractText, title: "卷宗要点抽取" });
      setExtractText("");
      await loadDetail(selectedId);
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "抽取完成", type: "success" } }),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "抽取失败");
    } finally {
      setBusy(false);
    }
  };

  const uploadExtract = async (file: File | null) => {
    if (!selectedId || !file) return;
    setBusy(true);
    setErr("");
    try {
      await api.extractMatterUpload(selectedId, file);
      await loadDetail(selectedId);
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "文件抽取完成", type: "success" } }),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "上传抽取失败");
    } finally {
      setBusy(false);
    }
  };

  const selected = items.find((x) => x.id === selectedId) || null;

  return (
    <div className="lead-panel matter-workspace">
      <h2>案件工作区</h2>
      <p className="muted">一案一档：备注、证据摘录、期限与生成草稿可挂接在此。</p>
      {err && <p className="form-msg error">{err}</p>}

      <div className="matter-layout">
        <div className="matter-list-col">
          <div className="lawyer-form matter-create">
            <label>
              案件标题 *
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：张某劳动争议" />
            </label>
            <label>
              案号
              <input value={caseNo} onChange={(e) => setCaseNo(e.target.value)} placeholder="可选" />
            </label>
            <label>
              案由/罪名
              <input value={cause} onChange={(e) => setCause(e.target.value)} placeholder="可选" />
            </label>
            <button className="btn-primary" type="button" disabled={busy || !title.trim()} onClick={() => void create()}>
              新建案件
            </button>
          </div>
          <ul className="lead-list">
            {items.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  className={`lead-card ${selectedId === m.id ? "active" : ""}`}
                  onClick={() => setSelectedId(m.id)}
                >
                  <div className="lead-card-top">
                    <strong>{m.title}</strong>
                    {m.overdue_count > 0 && <span className="src-tag st-repealed">逾期 {m.overdue_count}</span>}
                  </div>
                  <div className="lead-meta">
                    {m.case_no || "无案号"}
                    {m.cause ? ` · ${m.cause}` : ""}
                    {` · 材料 ${m.artifact_count} · 期限 ${m.deadline_count}`}
                  </div>
                </button>
              </li>
            ))}
          </ul>
          {items.length === 0 && <p className="muted">暂无案件，先新建一个。</p>}
        </div>

        <div className="matter-detail-col">
          {!selected ? (
            <p className="muted">选择左侧案件查看详情。</p>
          ) : (
            <>
              <div className="lead-card-top">
                <h3>{selected.title}</h3>
                <button type="button" className="btn-ghost" onClick={() => void removeMatter(selected.id)}>
                  删除
                </button>
              </div>
              <p className="muted">
                {selected.case_no || "无案号"}
                {selected.cause ? ` · ${selected.cause}` : ""} · {selected.status}
              </p>

              <section className="opinion-section">
                <h3>期限</h3>
                <ul className="event-list deadline-list">
                  {deadlines.map((d) => (
                    <li key={d.id} className={d.overdue && !d.done ? "deadline-overdue" : ""}>
                      <label className="deadline-row">
                        <input type="checkbox" checked={d.done} onChange={() => void toggleDeadline(d)} />
                        <span>
                          {d.label}
                          {d.due_date ? ` · ${d.due_date}` : ""}
                          {d.overdue && !d.done ? " · 已逾期" : ""}
                        </span>
                      </label>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() =>
                          void api.deleteMatterDeadline(selected.id, d.id).then(() => loadDetail(selected.id))
                        }
                      >
                        删
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="matter-inline-form">
                  <input value={dlLabel} onChange={(e) => setDlLabel(e.target.value)} placeholder="期限名称" />
                  <input type="date" value={dlDate} onChange={(e) => setDlDate(e.target.value)} />
                  <button type="button" className="btn-gold" disabled={busy} onClick={() => void addDeadline()}>
                    添加期限
                  </button>
                </div>
              </section>

              <section className="opinion-section">
                <h3>办案材料</h3>
                <ul className="event-list">
                  {artifacts.map((a) => (
                    <li key={a.id}>
                      <span className="event-type">{a.kind}</span> {a.title}
                      <span className="muted"> · {a.created_at}</span>
                      {a.kind === "extract" && a.payload?.dossier_text ? (
                        <pre className="matter-extract-preview">{String(a.payload.dossier_text)}</pre>
                      ) : null}
                      {a.kind === "note" && a.payload?.text ? (
                        <p className="law-excerpt">{String(a.payload.text)}</p>
                      ) : null}
                      {a.kind === "elements" && a.payload?.supplement_text ? (
                        <pre className="matter-extract-preview">{String(a.payload.supplement_text)}</pre>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <div className="lawyer-form">
                  <label>
                    备注标题
                    <input value={noteTitle} onChange={(e) => setNoteTitle(e.target.value)} />
                  </label>
                  <label>
                    备注内容
                    <textarea rows={3} value={noteBody} onChange={(e) => setNoteBody(e.target.value)} />
                  </label>
                  <button type="button" className="btn-primary" disabled={busy} onClick={() => void addNote()}>
                    保存备注
                  </button>
                </div>
              </section>

              <section className="opinion-section">
                <h3>卷宗要点抽取</h3>
                <p className="muted">粘贴笔录/起诉意见书摘录，或上传 pdf/docx/txt。</p>
                <textarea
                  rows={6}
                  value={extractText}
                  onChange={(e) => setExtractText(e.target.value)}
                  placeholder="粘贴卷宗材料…"
                />
                <div className="btn-row">
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy || extractText.trim().length < 20}
                    onClick={() => void runExtract()}
                  >
                    {busy ? "处理中…" : "抽取要点"}
                  </button>
                  <label className="btn-gold file-btn">
                    上传文件抽取
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.md"
                      hidden
                      onChange={(e) => void uploadExtract(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
