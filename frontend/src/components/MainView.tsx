// 主界面：同壳顶栏切换用户版/律师版 + 免责弹窗 + 风险条 + 案源

import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { useSessions } from "../hooks/useSessions";
import { api } from "../api/client";
import Sidebar from "./Sidebar";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import AdminPanel from "./AdminPanel";
import DisclaimerModal from "./DisclaimerModal";
import LawyerPanel from "./LawyerPanel";
import LeadPublishForm from "./LeadPublishForm";
import MyLeadsPanel from "./MyLeadsPanel";
import LawsSearchPanel from "./LawsSearchPanel";
import CasesSearchPanel from "./CasesSearchPanel";
import ScenesCatalogPanel from "./ScenesCatalogPanel";
import type { LawyerProfile, StatsResponse } from "../api/types";

interface Props {
  userId: string;
  username: string;
  isAdmin: boolean;
  onLogout: () => void;
}

type AppMode = "user" | "lawyer";
type UserTab = "chat" | "scenes" | "laws" | "cases" | "publish" | "my-leads";

export default function MainView({ userId, username, isAdmin, onLogout }: Props) {
  void userId;
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [view, setView] = useState<"chat" | "admin">("chat");
  const [appMode, setAppMode] = useState<AppMode>("user");
  const [userTab, setUserTab] = useState<UserTab>("chat");
  const [publishScene, setPublishScene] = useState("劳动用工");
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [lawyer, setLawyer] = useState<LawyerProfile | null>(null);
  const [riskBanner, setRiskBanner] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { messages, busy, activeSessionId, send, loadSession, newSession } = useChat();
  const sessionsCtrl = useSessions(activeSessionId, loadSession, newSession);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setToast(detail);
      setTimeout(() => setToast(null), 4000);
    };
    window.addEventListener("app:toast", handler);
    return () => window.removeEventListener("app:toast", handler);
  }, []);

  useEffect(() => {
    api.stats().then(setStats).catch(() => undefined);
    api
      .me()
      .then((u) => {
        if (!u.disclaimer_acked) setShowDisclaimer(true);
      })
      .catch(() => undefined);
    api.lawyerStatus().then(setLawyer).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const last = [...messages].reverse().find((m) => m.role === "assistant" && m.riskBanner);
    setRiskBanner(last?.riskBanner || "");
  }, [messages]);

  const handleAdminClick = () => {
    setView((v) => (v === "admin" ? "chat" : "admin"));
  };

  const switchMode = (mode: AppMode) => {
    setAppMode(mode);
    if (mode === "user") setUserTab("chat");
  };

  const goPublish = (scene?: string) => {
    if (scene) setPublishScene(scene);
    setAppMode("user");
    setUserTab("publish");
  };

  const ackDisclaimer = async () => {
    try {
      await api.disclaimerAck();
      setShowDisclaimer(false);
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : "确认失败", type: "error" });
    }
  };

  const readonlyLawyer = lawyer?.access === "pending_readonly";

  return (
    <div className="app theme-lawfirm">
      {showDisclaimer && <DisclaimerModal onAck={() => void ackDisclaimer()} />}
      {toast && <div className={`global-toast ${toast.type}`}>{toast.message}</div>}
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
              <h1>
                {view === "admin"
                  ? "管理后台"
                  : appMode === "lawyer"
                    ? "法律知识顾问 · 律师版"
                    : "法律知识顾问 · 用户版"}
              </h1>
              <p className="subtitle">
                {view === "admin"
                  ? "系统数据总览 · 用户/律师审核"
                  : "RAG 检索增强 · 引用可溯源 · 案源闭环"}
              </p>
            </div>
          </div>
          <div className="topbar-actions">
            {view === "chat" && (
              <div className="mode-switch">
                <button
                  type="button"
                  className={appMode === "user" ? "active" : ""}
                  onClick={() => switchMode("user")}
                >
                  用户版
                </button>
                <button
                  type="button"
                  className={appMode === "lawyer" ? "active" : ""}
                  onClick={() => switchMode("lawyer")}
                >
                  律师版
                </button>
              </div>
            )}
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
        ) : appMode === "lawyer" ? (
          <main className="chat-area lawyer-area">
            <div className="banner">
              ⚠️ AI 生成内容仅供参考，不构成正式法律意见。律师办案请以现行法规与个案事实为准。
            </div>
            <LawyerPanel readonlyMode={readonlyLawyer || lawyer?.access === "none"} />
          </main>
        ) : (
          <>
            <div className="banner">
              ⚠️ AI 生成内容仅供参考，不构成正式法律意见。具体案件请咨询专业法律人士。
            </div>
            <div className="sub-tabs user-tabs">
              <button type="button" className={userTab === "chat" ? "active" : ""} onClick={() => setUserTab("chat")}>
                AI 咨询
              </button>
              <button type="button" className={userTab === "scenes" ? "active" : ""} onClick={() => setUserTab("scenes")}>
                场景分类
              </button>
              <button type="button" className={userTab === "laws" ? "active" : ""} onClick={() => setUserTab("laws")}>
                法规检索
              </button>
              <button type="button" className={userTab === "cases" ? "active" : ""} onClick={() => setUserTab("cases")}>
                类案参考
              </button>
              <button type="button" className={userTab === "publish" ? "active" : ""} onClick={() => setUserTab("publish")}>
                发案源
              </button>
              <button type="button" className={userTab === "my-leads" ? "active" : ""} onClick={() => setUserTab("my-leads")}>
                我的案源
              </button>
            </div>
            {userTab === "chat" && (
              <>
                {riskBanner && <div className="risk-banner danger">{riskBanner}</div>}
                <main className="chat-area">
                  {messages.length === 0 && (
                    <div className="welcome">
                      <div className="welcome-icon">⚖️</div>
                      <h2>有什么法律问题想了解？</h2>
                      <p>
                        覆盖劳动、租房、婚姻、交通事故、消费、行政诉讼、合同等场景；复杂或高风险问题可发布案源对接律师。
                      </p>
                      <button type="button" className="cta-lawyer" onClick={() => goPublish()}>
                        直接发布案源需求
                      </button>
                    </div>
                  )}
                  {messages.map((m) => (
                    <MessageBubble
                      key={m.id}
                      message={m}
                      onSwitchLawyer={() => switchMode("lawyer")}
                      onPublishLead={(scene) => goPublish(scene)}
                    />
                  ))}
                  {busy && (
                    <div className="msg ai">
                      <div className="avatar">⚖️</div>
                      <div className="bubble typing">正在分析风险并检索知识库…</div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </main>
                <InputBar busy={busy} onSend={(t) => void send(t)} />
              </>
            )}
            {userTab === "scenes" && (
              <main className="chat-area lawyer-area">
                <ScenesCatalogPanel
                  onPickActive={(sceneId) => {
                    setPublishScene(sceneId);
                    setUserTab("chat");
                    window.dispatchEvent(
                      new CustomEvent("app:toast", {
                        detail: { message: `已选择场景「${sceneId}」，可直接提问或发案源`, type: "success" },
                      }),
                    );
                  }}
                />
              </main>
            )}
            {userTab === "laws" && (
              <main className="chat-area lawyer-area">
                <LawsSearchPanel />
              </main>
            )}
            {userTab === "cases" && (
              <main className="chat-area lawyer-area">
                <CasesSearchPanel />
              </main>
            )}
            {userTab === "publish" && (
              <main className="chat-area lawyer-area">
                <LeadPublishForm
                  defaultScene={publishScene}
                  onPublished={() => setUserTab("my-leads")}
                />
              </main>
            )}
            {userTab === "my-leads" && (
              <main className="chat-area lawyer-area">
                <MyLeadsPanel />
              </main>
            )}
          </>
        )}
      </div>
    </div>
  );
}
