// 主界面：按 role 硬进用户版 / 律师版 / 管理后台（无版本切换）

import { useEffect, useMemo, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { useSessions } from "../hooks/useSessions";
import { api, tokenStore } from "../api/client";
import Sidebar, { type NavItem } from "./Sidebar";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import SlotChoiceBar from "./SlotChoiceBar";
import AdminPanel from "./AdminPanel";
import DisclaimerModal from "./DisclaimerModal";
import ProWorkbench from "./ProWorkbench";
import LawyerApplyForm from "./LawyerApplyForm";
import LeadPublishForm from "./LeadPublishForm";
import MyLeadsPanel from "./MyLeadsPanel";
import LawsSearchPanel from "./LawsSearchPanel";
import CasesSearchPanel from "./CasesSearchPanel";
import ScenesCatalogPanel from "./ScenesCatalogPanel";
import TemplatesPanel from "./TemplatesPanel";
import CalculatorsPanel from "./CalculatorsPanel";
import type { LawyerProfile, StatsResponse } from "../api/types";

interface Props {
  userId: string;
  username: string;
  role: string;
  onLogout: () => void;
}

type Shell = "admin" | "pro" | "user";
type UserTab =
  | "chat"
  | "scenes"
  | "laws"
  | "cases"
  | "templates"
  | "calculators"
  | "publish"
  | "my-leads"
  | "apply";

const PRO_ROLES = new Set(["lawyer", "judge", "prosecutor"]);

const USER_NAV: NavItem[] = [
  { id: "chat", label: "问答" },
  { id: "scenes", label: "场景分类" },
  { id: "laws", label: "法规检索" },
  { id: "cases", label: "类案参考" },
  { id: "templates", label: "文书" },
  { id: "calculators", label: "计算器" },
  { id: "publish", label: "发案源" },
  { id: "my-leads", label: "我的案源" },
  { id: "apply", label: "职业认证" },
];

const LAWYER_NAV: NavItem[] = [
  { id: "ask", label: "问答" },
  { id: "leads", label: "案源" },
  { id: "opinion", label: "意见书" },
  { id: "contracts", label: "合同审查" },
  { id: "laws", label: "法规" },
  { id: "cases", label: "类案" },
  { id: "templates", label: "文书" },
  { id: "calculators", label: "计算器" },
  { id: "firm", label: "律所" },
];

const JUDGE_NAV: NavItem[] = [
  { id: "ask", label: "问答" },
  { id: "docket", label: "争点说理" },
  { id: "cases", label: "类案" },
  { id: "laws", label: "法规" },
  { id: "templates", label: "文书" },
  { id: "calculators", label: "期限费用" },
];

const PROSECUTOR_NAV: NavItem[] = [
  { id: "ask", label: "问答" },
  { id: "review", label: "审查报告" },
  { id: "cases", label: "类案" },
  { id: "laws", label: "法规" },
  { id: "templates", label: "文书" },
  { id: "calculators", label: "期限" },
];

function resolveShell(role: string, lawyer: LawyerProfile | null): Shell {
  if (role === "admin") return "admin";
  if (
    PRO_ROLES.has(role) ||
    lawyer?.access === "approved" ||
    lawyer?.status === "approved"
  ) {
    return "pro";
  }
  return "user";
}

function professionLabel(role: string, profile: LawyerProfile | null): string {
  const p = (profile?.profession || role || "").toLowerCase();
  if (p === "judge") return "法官版";
  if (p === "prosecutor") return "检察官版";
  return "律师版";
}

function defaultProTab(role: string, profile: LawyerProfile | null): string {
  const p = (profile?.profession || role || "").toLowerCase();
  if (p === "judge") return "ask";
  if (p === "prosecutor") return "ask";
  return "ask";
}

export default function MainView({ userId, username, role: roleProp, onLogout }: Props) {
  void userId;
  const [role, setRole] = useState(roleProp);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [userTab, setUserTab] = useState<UserTab>("chat");
  const [proTab, setProTab] = useState("ask");
  const [publishScene, setPublishScene] = useState("劳动用工");
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [lawyer, setLawyer] = useState<LawyerProfile | null>(null);
  const [riskBanner, setRiskBanner] = useState("");
  const [ready, setReady] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const chat = useChat();
  const { messages, busy, activeSessionId, send, loadSession, newSession, slotPrompt, clearSlot } =
    chat;
  const sessionsCtrl = useSessions(activeSessionId, loadSession, newSession);

  const shell = resolveShell(role, lawyer);

  const proNav = useMemo(() => {
    const p = (lawyer?.profession || role || "").toLowerCase();
    if (p === "judge") return JUDGE_NAV;
    if (p === "prosecutor") return PROSECUTOR_NAV;
    return LAWYER_NAV;
  }, [lawyer?.profession, role]);

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
    let cancelled = false;
    (async () => {
      try {
        const [u, lp] = await Promise.all([
          api.me().catch(() => null),
          api.lawyerStatus().catch(() => null),
        ]);
        if (cancelled) return;
        if (u) {
          setRole(u.role || roleProp);
          tokenStore.saveUser({
            username: u.username,
            user_id: u.id,
            role: u.role,
          });
          if (!u.disclaimer_acked) setShowDisclaimer(true);
        }
        if (lp) {
          setLawyer(lp);
          setProTab(defaultProTab(u?.role || roleProp, lp));
        }
        api.stats().then(setStats).catch(() => undefined);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [roleProp]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const last = [...messages].reverse().find((m) => m.role === "assistant" && m.riskBanner);
    setRiskBanner(last?.riskBanner || "");
  }, [messages]);

  const goPublish = (scene?: string) => {
    if (scene) setPublishScene(scene);
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

  if (!ready) {
    return (
      <div className="app theme-lawfirm">
        <div className="welcome" style={{ margin: "auto" }}>
          <p>正在加载工作台…</p>
        </div>
      </div>
    );
  }

  const title =
    shell === "admin"
      ? "法行宝 · 运营控制台"
      : shell === "pro"
        ? `法律知识顾问 · ${professionLabel(role, lawyer)}`
        : "法律知识顾问 · 用户版";
  const subtitle =
    shell === "admin"
      ? "认证审核 · 知识库 · 用户权限 · 问答质量"
      : shell === "pro"
        ? professionLabel(role, lawyer) === "律师版"
          ? "案源经营 · 意见书 · 合同审查"
          : "类案研究 · 法规检索 · 专业文书"
        : "RAG 检索增强 · 引用可溯源 · 案源闭环";

  // 从业者：问答会话区常驻侧边栏；用户版：仅在问答页显示
  const showSessions = shell === "pro" || (shell === "user" && userTab === "chat");

  const navItems = shell === "user" ? USER_NAV : shell === "pro" ? proNav : [];
  const activeNav = shell === "user" ? userTab : shell === "pro" ? proTab : undefined;
  const askNavId = shell === "user" ? "chat" : "ask";

  return (
    <div className="app theme-lawfirm">
      {showDisclaimer && shell !== "admin" && (
        <DisclaimerModal onAck={() => void ackDisclaimer()} />
      )}
      {toast && <div className={`global-toast ${toast.type}`}>{toast.message}</div>}
      {shell !== "admin" && (
        <Sidebar
          sessions={showSessions ? sessionsCtrl.sessions : []}
          activeId={showSessions ? activeSessionId : null}
          onSelectSession={(id) => {
            if (shell === "user") setUserTab("chat");
            if (shell === "pro") setProTab("ask");
            if (id) sessionsCtrl.select(id);
          }}
          onNewSession={() => {
            if (shell === "user") setUserTab("chat");
            if (shell === "pro") setProTab("ask");
            sessionsCtrl.create();
          }}
          onDeleteSession={(id) => {
            if (id === activeSessionId) newSession();
            void sessionsCtrl.remove(id);
          }}
          onLogout={onLogout}
          username={username}
          isAdmin={false}
          hideChats={false}
          showSessions={showSessions}
          askNavId={askNavId}
          shellLabel={
            shell === "pro" ? `${professionLabel(role, lawyer).replace("版", "")}工作台` : "法律知识问答"
          }
          navItems={navItems}
          activeNav={activeNav}
          onNavSelect={(id) => {
            if (shell === "user") setUserTab(id as UserTab);
            else setProTab(id);
          }}
        />
      )}

      <div className={`main-area ${shell === "admin" ? "main-area-admin" : ""}`}>
        {shell !== "admin" && (
          <header className="topbar">
            <div className="brand">
              <div>
                <h1>{title}</h1>
                <p className="subtitle">{subtitle}</p>
              </div>
            </div>
            <div className="topbar-actions">
              <span className="stat-pill shell-pill">
                {shell === "pro" ? professionLabel(role, lawyer) : "用户版"}
              </span>
              {shell === "user" && stats && (
                <span className="stat-pill">
                  {stats.doc_count} 文档 · {stats.chunk_count} 片段
                </span>
              )}
            </div>
          </header>
        )}

        {shell === "admin" && (
          <div className="admin-shell">
            <AdminPanel username={username} onLogout={onLogout} />
          </div>
        )}

        {shell === "pro" && (
          <main className="chat-area lawyer-area tool-panel-shell">
            <div className="banner">
              ⚠️ AI 生成内容仅供参考，不构成正式法律意见。办案请以现行法规与个案事实为准。
            </div>
            <ProWorkbench profile={lawyer} tab={proTab} chat={chat} />
          </main>
        )}

        {shell === "user" && (
          <>
            <div className="banner">
              ⚠️ AI 生成内容仅供参考，不构成正式法律意见。具体案件请咨询专业法律人士。
            </div>
            {(lawyer?.status === "pending" || lawyer?.access === "pending_readonly") && (
              <div className="risk-banner warn">
                职业认证审核中：通过后本账号将自动进入对应从业者工作台（律师 / 法官 / 检察官）。
              </div>
            )}
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
                {slotPrompt ? (
                  <SlotChoiceBar
                    busy={busy}
                    prompt={slotPrompt.prompt}
                    options={slotPrompt.options}
                    onChoose={(text) => void send(text)}
                    onCancel={clearSlot}
                  />
                ) : (
                  <InputBar busy={busy} onSend={(t) => void send(t)} />
                )}
              </>
            )}
            {userTab === "scenes" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <ScenesCatalogPanel
                  onPickActive={(sceneId) => {
                    setPublishScene(sceneId);
                    setUserTab("chat");
                    window.dispatchEvent(
                      new CustomEvent("app:toast", {
                        detail: {
                          message: `已选择场景「${sceneId}」，可直接提问或发案源`,
                          type: "success",
                        },
                      }),
                    );
                  }}
                />
              </main>
            )}
            {userTab === "laws" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <LawsSearchPanel />
              </main>
            )}
            {userTab === "cases" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <CasesSearchPanel />
              </main>
            )}
            {userTab === "templates" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <TemplatesPanel />
              </main>
            )}
            {userTab === "calculators" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <CalculatorsPanel />
              </main>
            )}
            {userTab === "publish" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <LeadPublishForm
                  defaultScene={publishScene}
                  onPublished={() => setUserTab("my-leads")}
                />
              </main>
            )}
            {userTab === "my-leads" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <MyLeadsPanel />
              </main>
            )}
            {userTab === "apply" && (
              <main className="chat-area lawyer-area tool-panel-shell">
                <LawyerApplyForm
                  profile={lawyer}
                  onUpdated={(p) => {
                    setLawyer(p);
                    if (p.status === "approved" || p.access === "approved") {
                      const nextRole = (p.profession || "lawyer").toLowerCase();
                      setRole(nextRole);
                      setProTab("ask");
                      tokenStore.saveUser({
                        username,
                        user_id: Number(userId) || 0,
                        role: nextRole,
                      });
                    }
                  }}
                />
              </main>
            )}
          </>
        )}
      </div>
    </div>
  );
}
