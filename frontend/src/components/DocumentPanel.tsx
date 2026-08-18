// 文档管理面板：上传 / 列表 / 删除

import { useRef, useState } from "react";
import { useDocuments } from "../hooks/useDocuments";

export default function DocumentPanel() {
  const { documents, loading, uploading, error, refresh, upload, remove } = useDocuments();
  const [toast, setToast] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await upload(file);
    setToast(res.message);
    setTimeout(() => setToast(null), 4000);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="doc-panel">
      <div className="doc-head">
        <h3>📄 知识库文档</h3>
        <button className="btn-ghost btn-sm" onClick={refresh} disabled={loading}>
          {loading ? "刷新中…" : "刷新"}
        </button>
      </div>

      <div className="doc-upload">
        <input ref={fileRef} type="file" accept=".docx,.pdf,.txt,.md" hidden onChange={onFile} />
        <button className="btn-primary" disabled={uploading} onClick={() => fileRef.current?.click()}>
          {uploading ? "上传解析中…" : "⬆ 上传文档"}
        </button>
        <span className="doc-hint">支持 docx / pdf / txt / md，扫描件自动 OCR</span>
      </div>

      {toast && <div className="doc-toast">{toast}</div>}
      {error && <div className="err-text">{error}</div>}

      <div className="doc-stats">
        共 {documents.length} 篇文档
      </div>

      <div className="doc-list">
        {documents.slice(0, 50).map((d) => (
          <div className="doc-item" key={d.doc_id}>
            <div className="doc-info">
              <span className="doc-title">{d.title}</span>
              <span className="doc-meta">
                {d.category} · {d.chunks} 块
              </span>
              {d.effective_status && d.effective_status !== "现行有效" && (
                <span className={`src-tag st-${statusCls(d.effective_status)}`}>
                  {d.effective_status}
                </span>
              )}
            </div>
            <button
              className="btn-ghost btn-sm btn-danger"
              onClick={() => void remove(d.doc_id)}
              title="删除该文档"
            >
              删除
            </button>
          </div>
        ))}
        {documents.length === 0 && !loading && (
          <div className="doc-empty">暂无文档，请上传或后台入库</div>
        )}
      </div>
    </div>
  );
}

function statusCls(status: string): string {
  if (status === "已废止") return "repealed";
  if (status === "已修订") return "revised";
  return "partial";
}
