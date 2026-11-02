// 左侧常驻侧边栏：问答（新对话+历史）在上，其他功能在下

import { useState } from "react";
import { api } from "../api/client";
import type { SessionItem } from "../api/types";

export interface NavItem {
  id: string;
  label: string;
}

interface Props {
  sessions: SessionItem[];
  activeId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onLogout: () => void;
  username: string;
  isAdmin?: boolean;
  hideChats?: boolean;
  shellLabel?: string;
  navItems?: NavItem[];
  activeNav?: string;
  onNavSelect?: (id: string) => void;
  /** 是否展示问答会话区（从业者常开） */
  showSessions?: boolean;
  /** 问答导航项 id，用于高亮「问答」 */
  askNavId?: string;
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
  hideChats = false,
  shellLabel,
  navItems = [],
  activeNav,
  onNavSelect,
  showSessions = true,
  askNavId = "ask",
}: Props) {
  const chatsVisible = !hideChats && showSessions;
  // 问答之外的工具入口（问答本身由上方会话区承担）
  const toolItems = navItems.filter((item) => item.id !== askNavId && item.id !== "chat");
  const askActive = activeNav === askNavId || activeNav === "chat";

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="logo">⚖️</span>
        <span className="sidebar-title">{shellLabel || "法律知识问答"}</span>
      </div>

      {chatsVisible && (
        <section className="sidebar-ask" aria-label="问答">
          <div className="sidebar-ask-head">
            <button
              type="button"
              className={`sidebar-ask-title ${askActive ? "active" : ""}`}
              onClick={() => onNavSelect?.(askNavId)}
            >
              问答
            </button>
            <button type="button" className="btn-new-chat btn-new-chat-compact" onClick={onNewSession}>
              新对话
            </button>
          </div>
          <ChatList
            sessions={sessions}
            activeId={activeId}
            askActive={askActive}
            onSelect={(id) => {
              onNavSelect?.(askNavId);
              onSelectSession(id);
            }}
            onDelete={onDeleteSession}
          />
        </section>
      )}

      {toolItems.length > 0 && (
        <nav className="sidebar-nav" aria-label="工作台功能">
          <div className="sidebar-nav-label">工作台</div>
          {toolItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-item ${activeNav === item.id ? "active" : ""}`}
              onClick={() => onNavSelect?.(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}

      {hideChats && navItems.length === 0 && (
        <div className="sidebar-body">
          <div className="sidebar-empty">管理后台 · 无问答入口</div>
        </div>
      )}

      <div className="sidebar-user">
        <span className="user-avatar">👤</span>
        <span className="user-name">
          {username}
          {isAdmin && <span className="admin-badge">管理员</span>}
        </span>
        <button className="btn-ghost btn-sm" onClick={onLogout}>
          退出
        </button>
      </div>
    </aside>
  );
}

function ChatList({
  sessions,
  activeId,
  askActive,
  onSelect,
  onDelete,
}: {
  sessions: SessionItem[];
  activeId: string | null;
  askActive: boolean;
  onSelect: (id: string) => void;
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
    <div className="sidebar-ask-body">
      {sessions.length > 0 && (
        <div className="chat-toolbar chat-toolbar-mini">
          <button
            type="button"
            className={`btn-manage ${manage ? "active" : ""}`}
            onClick={() => {
              setManage((v) => !v);
              setSelected(new Set());
            }}
          >
            {manage ? "取消" : "管理"}
          </button>
        </div>
      )}

      {manage && sessions.length > 0 && (
        <div className="manage-bar">
          <label className="manage-all">
            <input
              type="checkbox"
              checked={selected.size === sessions.length && sessions.length > 0}
              onChange={toggleAll}
            />
            全选
          </label>
          <span className="manage-count">已选 {selected.size}</span>
          <button className="manage-delete" disabled={selected.size === 0} onClick={deleteSelected}>
            删除
          </button>
        </div>
      )}

      <div className="chat-list">
        {sessions.length === 0 && (
          <div className="sidebar-empty">暂无会话，点「新对话」开始检索</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`chat-item ${askActive && activeId === s.id ? "active" : ""} ${manage && selected.has(s.id) ? "selected" : ""}`}
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
                {s.msg_count} 条 · {formatTime(s.updated_at)}
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
