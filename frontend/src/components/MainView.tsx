// 主界面：侧边栏（对话历史/知识库/管理后台）+ 主视图（聊天/后台）
// 注意：此组件以 userId 为 key 挂载，登录用户切换时完全重建

import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { useSessions } from "../hooks/useSessions";
import { api } from "../api/client";
import Sidebar from "./Sidebar";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import AdminPanel from "./AdminPanel";
import type { StatsResponse } from "../api/types";

interface Props {
  userId: string;
  username: string;
  isAdmin: boolean;
  onLogout: () => void;
}

export default function MainView({ userId, username, isAdmin, onLogout }: Props) {
  // userId 仅用于 React key 强制重挂载，此处保留避免 lint 报错
  void userId;
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [view, setView] = useState<"chat" | "admin">("chat");
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { messages, busy, activeSessionId, send, loadSession, newSession } = useChat();
  const sessionsCtrl = useSessions(activeSessionId, loadSession, newSession);

  // 全局 toast（网络错误 / 操作失败提示）
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setToast(detail);
      setTimeout(() => setToast(null), 4000);
    };
    window.addEventListener("app:toast", handler);
    return () => window.removeEventListener("app:toast", handler);
  }, []);

  // 知识库统计
  useEffect(() => {
    api.stats().then(setStats).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const handleAdminClick = () => {
    setView((v) => (v === "admin" ? "chat" : "admin"));
  };

  return (
    <div className="app">
      {toast && (
        <div className={`global-toast ${toast.type}`}>{toast.message}</div>
      )}
      <Sidebar
        sessions={sessionsCtrl.sessions}
        activeId={activeSessionId}
        onSelectSession={sessionsCtrl.select}
        onNewSession={sessionsCtrl.create}
        onDeleteSession={(id) => {
          if (id === activeSessionId) newSession();
          void sessionsCtrl.remove(id);
        }}
        onLogout={onLogout}
        username={username}
        isAdmin={isAdmin}
        onAdminClick={isAdmin ? handleAdminClick : undefined}
        adminActive={view === "admin"}
      />

      <div className="main-area">
        <header className="topbar">
          <div className="brand">
            <div>
              <h1>{view === "admin" ? "管理后台" : "法律知识问答助手"}</h1>
              <p className="subtitle">
                {view === "admin"
                  ? "系统数据总览 · 用户管理"
                  : "基于 RAG 检索增强生成 · 引用可溯源"}
              </p>
            </div>
          </div>
          <div className="topbar-actions">
            {view === "chat" && stats && (
              <span className="stat-pill">
                {stats.doc_count} 文档 · {stats.chunk_count} 片段
              </span>
            )}
          </div>
        </header>

        {view === "admin" ? (
          <div className="admin-scroll">
            <AdminPanel />
          </div>
        ) : (
          <>
            <div className="banner">
              ⚠️ AI 生成内容仅供参考，不构成正式法律意见。具体案件请咨询专业法律人士。
            </div>
            <main className="chat-area">
              {messages.length === 0 && (
                <div className="welcome">
                  <div className="welcome-icon">⚖️</div>
                  <h2>有什么法律问题想了解？</h2>
                  <p>
                    可询问具体法条、司法解释、行政处罚规定等，回答将附带引用来源与相似案例推荐。
                  </p>
                </div>
              )}
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {busy && (
                <div className="msg ai">
                  <div className="avatar">⚖️</div>
                  <div className="bubble typing">正在检索知识库并生成回答…</div>
                </div>
              )}
              <div ref={bottomRef} />
            </main>

            <InputBar busy={busy} onSend={(t) => void send(t)} />
          </>
        )}
      </div>
    </div>
  );
}
