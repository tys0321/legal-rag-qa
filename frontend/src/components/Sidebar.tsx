// 左侧常驻侧边栏：对话历史 + 知识库管理两个区域

import { useRef, useState } from "react";
import { api } from "../api/client";
import { useDocuments } from "../hooks/useDocuments";
import type { SessionItem } from "../api/types";

interface Props {
  sessions: SessionItem[];
  activeId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onLogout: () => void;
  username: string;
  isAdmin?: boolean;
  onAdminClick?: () => void;
  adminActive?: boolean;
}

export default function Sidebar({
  sessions,
  activeId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onLogout,
  username,
  isAdmin = false,
  onAdminClick,
  adminActive = false,
}: Props) {
  const [tab, setTab] = useState<"chats" | "kb">("chats");

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="logo">⚖️</span>
        <span className="sidebar-title">法律知识问答</span>
      </div>

      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${tab === "chats" ? "active" : ""}`}
          onClick={() => setTab("chats")}
        >
          💬 对话
        </button>
        <button
          className={`sidebar-tab ${tab === "kb" ? "active" : ""}`}
          onClick={() => setTab("kb")}
        >
          📚 知识库
        </button>
      </div>

      {tab === "chats" ? (
        <ChatsTab
          sessions={sessions}
          activeId={activeId}
          onSelect={onSelectSession}
          onNew={onNewSession}
          onDelete={onDeleteSession}
        />
      ) : (
        <KbTab />
      )}

      <div className="sidebar-user">
        <span className="user-avatar">👤</span>
        <span className="user-name">
          {username}
          {isAdmin && <span className="admin-badge">管理员</span>}
        </span>
        {isAdmin && onAdminClick && (
          <button
            className={`btn-ghost btn-sm ${adminActive ? "admin-active" : ""}`}
            onClick={onAdminClick}
          >
            {adminActive ? "返回问答" : "🛡️ 后台"}
          </button>
        )}
        <button className="btn-ghost btn-sm" onClick={onLogout}>
          退出
        </button>
      </div>
    </aside>
  );
}

function ChatsTab({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: {
  sessions: SessionItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  const [manage, setManage] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === sessions.length ? new Set() : new Set(sessions.map((s) => s.id)),
    );
  };

  const deleteSelected = () => {
    if (selected.size === 0) return;
    if (!confirm(`确定删除选中的 ${selected.size} 个会话？此操作不可恢复。`)) return;
    const ids = [...selected];
    api
      .batchDeleteSessions(ids)
      .then(() => {
        ids.forEach((id) => {
          if (id === activeId) onSelect("");
        });
        setSelected(new Set());
        setManage(false);
        window.dispatchEvent(new CustomEvent("sessions:changed"));
      })
      .catch(() => alert("删除失败"));
  };

  return (
    <div className="sidebar-body">
      <div className="chat-toolbar">
        <button className="btn-new-chat" onClick={onNew}>
          ＋ 新对话
        </button>
        {sessions.length > 0 && (
          <button
            className={`btn-manage ${manage ? "active" : ""}`}
            onClick={() => {
              setManage((v) => !v);
              setSelected(new Set());
            }}
          >
            {manage ? "取消" : "管理"}
          </button>
        )}
      </div>

      {manage && sessions.length > 0 && (
        <div className="manage-bar">
          <label className="manage-all">
            <input type="checkbox" checked={selected.size === sessions.length} onChange={toggleAll} />
            全选
          </label>
          <span className="manage-count">已选 {selected.size} 项</span>
          <button
            className="manage-delete"
            disabled={selected.size === 0}
            onClick={deleteSelected}
          >
            删除选中
          </button>
        </div>
      )}

      <div className="chat-list">
        {sessions.length === 0 && (
          <div className="sidebar-empty">暂无历史对话，开始一个新对话吧</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`chat-item ${activeId === s.id ? "active" : ""} ${manage && selected.has(s.id) ? "selected" : ""}`}
            onClick={() => {
              if (manage) toggle(s.id);
              else onSelect(s.id);
            }}
          >
            {manage && (
              <input
                type="checkbox"
                className="chat-check"
                checked={selected.has(s.id)}
                onChange={() => toggle(s.id)}
                onClick={(e) => e.stopPropagation()}
              />
            )}
            <div className="chat-item-main">
              <div className="chat-item-title">{s.title}</div>
              <div className="chat-item-meta">
                {s.msg_count} 条消息 · {formatTime(s.updated_at)}
              </div>
            </div>
            {!manage && (
              <button
                className="chat-item-del"
                title="删除会话"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("确定删除该会话？")) onDelete(s.id);
                }}
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function KbTab() {
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
    <div className="sidebar-body kb-body">
      <input
        ref={fileRef}
        type="file"
        accept=".docx,.pdf,.txt,.md"
        hidden
        onChange={onFile}
      />
      <button
        className="btn-upload"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
      >
        {uploading ? "上传解析中…" : "⬆ 上传文档"}
      </button>
      <div className="kb-hint">支持 docx / pdf / txt / md，扫描件自动 OCR</div>

      {toast && <div className="kb-toast">{toast}</div>}
      {error && <div className="err-text">{error}</div>}

      <div className="kb-count">共 {documents.length} 篇文档</div>
      <div className="kb-list">
        {documents.slice(0, 200).map((d) => (
          <div className="kb-item" key={d.doc_id}>
            <div className="kb-info">
              <div className="kb-title" title={d.title}>
                {d.title}
              </div>
              <div className="kb-meta">
                {d.category} · {d.chunks} 块
                {d.effective_status && d.effective_status !== "现行有效" && (
                  <span className={`src-tag st-${statusCls(d.effective_status)}`}>
                    {d.effective_status}
                  </span>
                )}
              </div>
            </div>
            <button
              className="chat-item-del"
              title="删除文档"
              onClick={() => {
                if (confirm(`确定从知识库删除「${d.title}」？`)) void remove(d.doc_id);
              }}
            >
              ✕
            </button>
          </div>
        ))}
        {documents.length === 0 && !loading && (
          <div className="sidebar-empty">暂无文档</div>
        )}
      </div>
      <button className="btn-refresh" onClick={refresh} disabled={loading}>
        {loading ? "刷新中…" : "🔄 刷新列表"}
      </button>
    </div>
  );
}

function statusCls(status: string): string {
  if (status === "已废止") return "repealed";
  if (status === "已修订") return "revised";
  return "partial";
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso.replace(" ", "T"));
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      return d.toTimeString().slice(0, 5);
    }
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  } catch {
    return iso.slice(5, 16);
  }
}
