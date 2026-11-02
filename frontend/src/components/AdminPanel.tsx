// 运营控制台：侧栏分模块 · 总览待办 · 律师审核工作台 · 用户/知识库/反馈/运维

import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type MouseEvent,
} from "react";
import { createPortal } from "react-dom";
import { api } from "../api/client";
import { useDocuments } from "../hooks/useDocuments";
import AdminDashboard from "./AdminDashboard";
import type {
  AdminAccess,
  AdminLogItem,
  AdminUserItem,
  DashboardData,
  FeedbackDetail,
  FeedbackItem,
  LawyerProfile,
  SnapshotItem,
  SystemStatus,
} from "../api/types";

type PermMenu = { user: AdminUserItem; picked: string[] };
type AdminNav =
  | "overview"
  | "lawyers"
  | "users"
  | "kb"
  | "feedbacks"
  | "ops";
type LawyerSub = "pending" | "approved";
type OpsSub = "status" | "backups" | "logs";

interface AdminPanelProps {
  username?: string;
  onLogout?: () => void;
}

const NAV: { id: AdminNav; label: string; icon: string; perm?: string; desc: string }[] = [
  { id: "overview", label: "运营总览", icon: "▣", desc: "数据看板 · 趋势与分布" },
  { id: "lawyers", label: "职业认证", icon: "⚖", perm: "lawyers", desc: "审核律师/法官/检察官材料" },
  { id: "users", label: "用户与权限", icon: "◎", perm: "users", desc: "账号管理与管理员授权" },
  { id: "kb", label: "知识库", icon: "☰", perm: "kb", desc: "法规入库、检索片段维护" },
  { id: "feedbacks", label: "问答反馈", icon: "◈", perm: "feedbacks", desc: "用户对回答的评价与抽检" },
  { id: "ops", label: "系统运维", icon: "⚙", desc: "状态 · 备份 · 操作日志" },
];

const PROF_LABEL: Record<string, string> = {
  lawyer: "律师",
  judge: "法官",
  prosecutor: "检察官",
};

function matchLawyer(p: LawyerProfile, q: string): boolean {
  if (!q) return true;
  const hay = [
    p.username || "",
    String(p.user_id),
    p.profession || "",
    PROF_LABEL[p.profession || ""] || "",
    p.license_no || "",
    p.region || "",
    ...(p.specialties || []),
  ]
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
}

function paginate<T>(items: T[], page: number, pageSize: number) {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(page, pageCount);
  return {
    pageCount,
    safePage,
    slice: items.slice((safePage - 1) * pageSize, safePage * pageSize),
  };
}

export default function AdminPanel({ username = "", onLogout }: AdminPanelProps) {
  const [nav, setNav] = useState<AdminNav>("overview");
  const [lawyerSub, setLawyerSub] = useState<LawyerSub>("pending");
  const [opsSub, setOpsSub] = useState<OpsSub>("status");
  const [access, setAccess] = useState<AdminAccess | null>(null);
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashDays, setDashDays] = useState(14);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [pendingLawyers, setPendingLawyers] = useState<LawyerProfile[]>([]);
  const [approvedLawyers, setApprovedLawyers] = useState<LawyerProfile[]>([]);
  const [lawyerDetailId, setLawyerDetailId] = useState<number | null>(null);
  const [selectedPending, setSelectedPending] = useState<number[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [fbStats, setFbStats] = useState({ total: 0, useful: 0, useless: 0 });
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<
    "all" | "admin" | "user" | "lawyer" | "judge" | "prosecutor"
  >("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pendingSearch, setPendingSearch] = useState("");
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingPageSize, setPendingPageSize] = useState(10);
  const [approvedSearch, setApprovedSearch] = useState("");
  const [approvedPage, setApprovedPage] = useState(1);
  const [approvedPageSize, setApprovedPageSize] = useState(10);
  const [menu, setMenu] = useState<PermMenu | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastSynced, setLastSynced] = useState<string | null>(null);
  const [fbFilter, setFbFilter] = useState<"all" | "useful" | "useless">("all");
  const [fbOpenId, setFbOpenId] = useState<number | null>(null);
  const [fbDetail, setFbDetail] = useState<FeedbackDetail | null>(null);
  const [fbDetailLoading, setFbDetailLoading] = useState(false);

  const can = useCallback(
    (key: string) => !!access && (access.is_root || access.permissions.includes(key)),
    [access],
  );

  const roleMix = useMemo(() => {
    const mix = { user: 0, lawyer: 0, judge: 0, prosecutor: 0, admin: 0 };
    for (const u of users) {
      if (u.role === "lawyer") mix.lawyer += 1;
      else if (u.role === "judge") mix.judge += 1;
      else if (u.role === "prosecutor") mix.prosecutor += 1;
      else if (u.role === "admin") mix.admin += 1;
      else mix.user += 1;
    }
    return mix;
  }, [users]);

  const filteredFeedbacks = useMemo(() => {
    if (fbFilter === "all") return feedbacks;
    return feedbacks.filter((f) => f.rating === fbFilter);
  }, [feedbacks, fbFilter]);

  const toggleFeedbackDetail = async (id: number) => {
    if (fbOpenId === id) {
      setFbOpenId(null);
      setFbDetail(null);
      return;
    }
    setFbOpenId(id);
    setFbDetail(null);
    setFbDetailLoading(true);
    try {
      const d = await api.adminFeedbackDetail(id);
      setFbDetail(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载反馈详情失败");
      setFbOpenId(null);
    } finally {
      setFbDetailLoading(false);
    }
  };

  const visibleNav = useMemo(
    () =>
      NAV.filter((item) => {
        if (!item.perm) {
          if (item.id === "ops") {
            return can("status") || can("backups") || can("logs");
          }
          if (item.id === "overview") {
            return can("stats") || can("lawyers") || can("feedbacks") || can("status");
          }
          return true;
        }
        return can(item.perm);
      }),
    [can],
  );

  useEffect(() => {
    if (!visibleNav.some((n) => n.id === nav) && visibleNav[0]) {
      setNav(visibleNav[0].id);
    }
  }, [visibleNav, nav]);

  const refresh = useCallback(async () => {
    setError(null);
    setRefreshing(true);
    try {
      const acc = await api.adminAccess();
      setAccess(acc);
      const allow = (key: string) => acc.is_root || acc.permissions.includes(key);
      const [u, dash, st, lw, ap, fb] = await Promise.all([
        allow("users") ? api.adminUsers() : Promise.resolve({ users: [] as AdminUserItem[] }),
        allow("stats")
          ? api.adminDashboard(dashDays).catch(() => null)
          : Promise.resolve(null),
        allow("status") ? api.adminStatus() : Promise.resolve(null),
        allow("lawyers")
          ? api.adminLawyerPending().catch(() => ({ items: [] as LawyerProfile[] }))
          : Promise.resolve({ items: [] as LawyerProfile[] }),
        allow("lawyers")
          ? api.adminLawyerApproved().catch(() => ({ items: [] as LawyerProfile[] }))
          : Promise.resolve({ items: [] as LawyerProfile[] }),
        allow("feedbacks")
          ? api
              .adminFeedbacks(80)
              .catch(() => ({ total: 0, useful: 0, useless: 0, items: [] as FeedbackItem[] }))
          : Promise.resolve({ total: 0, useful: 0, useless: 0, items: [] as FeedbackItem[] }),
      ]);
      setUsers(u.users);
      if (dash) setDashboard(dash);
      setStatus(st);
      setPendingLawyers(lw.items || []);
      setApprovedLawyers(ap.items || []);
      setSelectedPending([]);
      setFeedbacks(fb.items || []);
      setFbStats({ total: fb.total, useful: fb.useful, useless: fb.useless });
      setLastSynced(
        new Date().toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setRefreshing(false);
    }
  }, [dashDays]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const loadDashboard = (days: number) => {
    setDashDays(days);
  };

  const batchReview = async (approve: boolean) => {
    if (selectedPending.length === 0) return;
    const action = approve ? "通过" : "驳回";
    if (!confirm(`确定批量${action}选中的 ${selectedPending.length} 份申请？`)) return;
    setBatchBusy(true);
    setError(null);
    try {
      const r = await api.adminLawyerBatchReview(
        selectedPending,
        approve,
        approve ? "" : "材料不完整",
      );
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: {
            message: `批量${action}完成：成功 ${r.ok}，失败 ${r.fail}`,
            type: r.fail ? "warn" : "success",
          },
        }),
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "批量审核失败");
    } finally {
      setBatchBusy(false);
    }
  };

  useEffect(() => {
    if (!menu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenu(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menu]);

  const setRole = async (user: AdminUserItem, role: string, permissions: string[] = []) => {
    try {
      await api.adminSetRole(user.id, role, permissions);
      setMenu(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  };

  const revokeAdmin = async (user: AdminUserItem) => {
    if (!confirm(`确定撤销「${user.username}」的管理员？撤销后需重新登录，且不再能进后台。`)) return;
    await setRole(user, "user");
  };

  const openPermMenu = (event: MouseEvent, user: AdminUserItem) => {
    if (!access?.is_root || user.is_root) return;
    event.preventDefault();
    event.stopPropagation();
    const catalog = access.catalog.map((c) => c.key);
    const current = (user.permissions || []).filter((k) => catalog.includes(k));
    setMenu({
      user,
      picked: current.length ? current : catalog.slice(0, 1),
    });
  };

  const removeUser = async (user: AdminUserItem) => {
    if (!confirm(`确定删除用户「${user.username}」？其所有会话与消息将一并删除。`)) return;
    try {
      await api.adminDeleteUser(user.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  };

  const openLawyerFile = async (userId: number, filename: string) => {
    try {
      const blob = await api.adminLawyerFile(userId, filename);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "打开材料失败");
    }
  };

  const revokeLawyer = async (p: LawyerProfile) => {
    const name = p.username || `用户#${p.user_id}`;
    if (!confirm(`确定撤销「${name}」的律师认证？撤销后其律师写操作将不可用。`)) return;
    try {
      await api.adminLawyerRevoke(p.user_id, "管理员撤销认证");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "撤销失败");
    }
  };

  const renderLawyerMaterials = (p: LawyerProfile) => {
    const files = p.license_files || [];
    if (files.length === 0) {
      return <div className="au-meta">未上传执业证材料（演示申请或仅填了文本信息）</div>;
    }
    return (
      <div className="lawyer-files">
        {files.map((f) => (
          <button
            key={f}
            type="button"
            className="btn-sm lawyer-file-btn"
            onClick={() => void openLawyerFile(p.user_id, f)}
          >
            查看 {f.split(".").pop()?.toUpperCase() || "文件"}
          </button>
        ))}
      </div>
    );
  };

  const q = search.trim().toLowerCase();
  const filteredUsers = users.filter((u) => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false;
    if (!q) return true;
    return (
      u.username.toLowerCase().includes(q) || String(u.id).includes(q) || u.role.includes(q)
    );
  });
  const { pageCount, safePage, slice: pagedUsers } = paginate(filteredUsers, page, pageSize);

  const exportUsersCsv = () => {
    const header = ["id", "username", "role", "sessions", "messages", "created_at"];
    const rows = filteredUsers.map((u) =>
      [u.id, u.username, u.role, u.session_count, u.message_count, u.created_at]
        .map((c) => `"${String(c).replace(/"/g, '""')}"`)
        .join(","),
    );
    const blob = new Blob([[header.join(","), ...rows].join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `users-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const pendingQ = pendingSearch.trim().toLowerCase();
  const filteredPending = pendingLawyers.filter((p) => matchLawyer(p, pendingQ));
  const {
    pageCount: pendingPageCount,
    safePage: pendingSafePage,
    slice: pagedPending,
  } = paginate(filteredPending, pendingPage, pendingPageSize);

  const approvedQ = approvedSearch.trim().toLowerCase();
  const filteredApproved = approvedLawyers.filter((p) => matchLawyer(p, approvedQ));
  const {
    pageCount: approvedPageCount,
    safePage: approvedSafePage,
    slice: pagedApproved,
  } = paginate(filteredApproved, approvedPage, approvedPageSize);

  const usefulRate =
    fbStats.total > 0 ? Math.round((fbStats.useful / fbStats.total) * 100) : null;

  const renderListToolbar = (
    value: string,
    onSearch: (v: string) => void,
    size: number,
    onSize: (n: number) => void,
    placeholder: string,
  ) => (
    <div className="au-toolbar">
      <input
        className="au-search"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onSearch(e.target.value)}
      />
      <div className="au-filters">
        <select
          className="au-page-size"
          value={size}
          onChange={(e) => onSize(Number(e.target.value))}
          aria-label="每页条数"
        >
          <option value={10}>每页 10</option>
          <option value={20}>每页 20</option>
          <option value={50}>每页 50</option>
        </select>
      </div>
    </div>
  );

  const renderListPager = (
    filteredLen: number,
    safe: number,
    count: number,
    setPg: (fn: (p: number) => number) => void,
  ) =>
    filteredLen > 0 ? (
      <div className="au-pager">
        <button
          type="button"
          className="btn-sm"
          disabled={safe <= 1}
          onClick={() => setPg((p) => Math.max(1, p - 1))}
        >
          上一页
        </button>
        <span className="au-pager-info">
          第 {safe} / {count} 页 · 共 {filteredLen} 人
        </span>
        <button
          type="button"
          className="btn-sm"
          disabled={safe >= count}
          onClick={() => setPg((p) => Math.min(count, p + 1))}
        >
          下一页
        </button>
      </div>
    ) : null;

  const pageMeta = NAV.find((n) => n.id === nav);

  return (
    <div className="admin-console">
      <aside className="ac-nav">
        <div className="ac-brand">
          <div className="ac-brand-mark">法</div>
          <div>
            <div className="ac-brand-title">运营控制台</div>
            <div className="ac-brand-sub">
              {access?.is_root ? "根管理员" : "管理员"}
              {username ? ` · ${username}` : ""}
            </div>
          </div>
        </div>
        <nav className="ac-nav-list" aria-label="后台模块">
          {visibleNav.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`ac-nav-item ${nav === item.id ? "active" : ""}`}
              onClick={() => setNav(item.id)}
            >
              <span className="ac-nav-ico" aria-hidden>
                {item.icon}
              </span>
              <span className="ac-nav-label">{item.label}</span>
              {item.id === "lawyers" && pendingLawyers.length > 0 && (
                <span className="ac-nav-badge">{pendingLawyers.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="ac-nav-foot">
          {lastSynced && <div className="ac-sync">最近同步 {lastSynced}</div>}
          <button
            type="button"
            className="ac-btn-refresh"
            disabled={refreshing}
            onClick={() => void refresh()}
          >
            {refreshing ? "同步中…" : "刷新数据"}
          </button>
          {onLogout && (
            <button type="button" className="ac-btn-logout" onClick={onLogout}>
              退出登录
            </button>
          )}
        </div>
      </aside>

      <div className="ac-main">
        <header className="ac-top">
          <div>
            <h2>{pageMeta?.label || "控制台"}</h2>
            <p>{pageMeta?.desc}</p>
          </div>
          <div className="ac-top-right">
            {nav === "lawyers" && can("lawyers") && (
              <div className="ac-subtabs">
                <button
                  type="button"
                  className={lawyerSub === "pending" ? "active" : ""}
                  onClick={() => setLawyerSub("pending")}
                >
                  待审 {pendingLawyers.length}
                </button>
                <button
                  type="button"
                  className={lawyerSub === "approved" ? "active" : ""}
                  onClick={() => setLawyerSub("approved")}
                >
                  已通过 {approvedLawyers.length}
                </button>
              </div>
            )}
            {nav === "ops" && (
              <div className="ac-subtabs">
                {can("status") && (
                  <button
                    type="button"
                    className={opsSub === "status" ? "active" : ""}
                    onClick={() => setOpsSub("status")}
                  >
                    系统状态
                  </button>
                )}
                {can("backups") && (
                  <button
                    type="button"
                    className={opsSub === "backups" ? "active" : ""}
                    onClick={() => setOpsSub("backups")}
                  >
                    数据备份
                  </button>
                )}
                {can("logs") && (
                  <button
                    type="button"
                    className={opsSub === "logs" ? "active" : ""}
                    onClick={() => setOpsSub("logs")}
                  >
                    操作日志
                  </button>
                )}
              </div>
            )}
            <button
              type="button"
              className="ac-top-refresh"
              disabled={refreshing}
              onClick={() => void refresh()}
            >
              {refreshing ? "同步中" : "同步"}
            </button>
          </div>
        </header>

        {error && <div className="err-text ac-error">{error}</div>}

        <div className="ac-body">
          {nav === "overview" && (
            can("stats") ? (
              dashboard ? (
                <AdminDashboard
                  data={dashboard}
                  days={dashDays}
                  onDaysChange={loadDashboard}
                  onGoto={(id) => {
                    if (id === "lawyers") {
                      setNav("lawyers");
                      setLawyerSub("pending");
                    } else if (id === "ops") {
                      setNav("ops");
                      setOpsSub("status");
                    } else {
                      setNav(id);
                    }
                  }}
                />
              ) : (
                <div className="bk-empty">看板数据加载中…</div>
              )
            ) : (
              <div className="bk-empty">当前账号无「系统统计」权限，无法查看数据看板。</div>
            )
          )}

          {nav === "lawyers" && can("lawyers") && (
            <div className="admin-section ac-section-flush">
              {lawyerSub === "pending" ? (
                <>
                  <p className="bk-hint">
                    核对证号与附件后审核；通过后该账号固定进入对应职业工作台（律师/法官/检察官）。
                  </p>
                  {renderListToolbar(
                    pendingSearch,
                    (v) => {
                      setPendingSearch(v);
                      setPendingPage(1);
                    },
                    pendingPageSize,
                    (n) => {
                      setPendingPageSize(n);
                      setPendingPage(1);
                    },
                    "搜索用户名 / ID / 证号 / 地区 / 擅长…",
                  )}
                  {pendingLawyers.length === 0 ? (
                    <div className="bk-empty">暂无待审申请</div>
                  ) : filteredPending.length === 0 ? (
                    <div className="bk-empty">无匹配结果</div>
                  ) : (
                    <>
                      <div className="lw-table-wrap">
                        <table className="lw-table">
                          <thead>
                            <tr>
                              <th className="lw-col-check">
                                <input
                                  type="checkbox"
                                  aria-label="全选"
                                  checked={filteredPending.every((p) =>
                                    selectedPending.includes(p.user_id),
                                  )}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedPending(filteredPending.map((p) => p.user_id));
                                    } else {
                                      setSelectedPending([]);
                                    }
                                  }}
                                />
                              </th>
                              <th className="lw-col-user">申请人</th>
                              <th className="lw-col-prof">职业</th>
                              <th className="lw-col-license">证号</th>
                              <th className="lw-col-region">地区</th>
                              <th className="lw-col-spec">擅长</th>
                              <th className="lw-col-files">材料</th>
                              <th className="lw-col-actions">操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pagedPending.map((p) => {
                              const open = lawyerDetailId === p.user_id;
                              const fileCount = (p.license_files || []).length;
                              const checked = selectedPending.includes(p.user_id);
                              const specs = (p.specialties || []).join("、") || "—";
                              return (
                                <Fragment key={p.user_id}>
                                  <tr className={open ? "is-open" : undefined}>
                                    <td className="lw-col-check">
                                      <input
                                        type="checkbox"
                                        checked={checked}
                                        onChange={(e) => {
                                          setSelectedPending((prev) =>
                                            e.target.checked
                                              ? [...prev, p.user_id]
                                              : prev.filter((id) => id !== p.user_id),
                                          );
                                        }}
                                      />
                                    </td>
                                    <td className="lw-col-user">
                                      <div className="lw-user">
                                        <strong>{p.username || `用户#${p.user_id}`}</strong>
                                        <span>#{p.user_id}</span>
                                      </div>
                                    </td>
                                    <td className="lw-col-prof">
                                      <span className="lw-prof-badge">
                                        {PROF_LABEL[p.profession || "lawyer"] || "律师"}
                                      </span>
                                    </td>
                                    <td className="lw-col-license">
                                      <code>{p.license_no || "—"}</code>
                                    </td>
                                    <td className="lw-col-region">{p.region || "—"}</td>
                                    <td className="lw-col-spec" title={specs}>
                                      {specs}
                                    </td>
                                    <td className="lw-col-files">
                                      <span className={fileCount ? "lw-file-ok" : "lw-file-none"}>
                                        {fileCount ? `${fileCount} 份` : "无"}
                                      </span>
                                    </td>
                                    <td className="lw-col-actions">
                                      <div className="lw-ops">
                                        <button
                                          type="button"
                                          className="lw-link"
                                          onClick={() =>
                                            setLawyerDetailId(open ? null : p.user_id)
                                          }
                                        >
                                          {open ? "收起" : "资料"}
                                        </button>
                                        <button
                                          type="button"
                                          className="lw-link ok"
                                          onClick={() =>
                                            void api
                                              .adminLawyerReview(p.user_id, true)
                                              .then(refresh)
                                              .catch((e) =>
                                                setError(
                                                  e instanceof Error ? e.message : "审核失败",
                                                ),
                                              )
                                          }
                                        >
                                          通过
                                        </button>
                                        <button
                                          type="button"
                                          className="lw-link danger"
                                          onClick={() =>
                                            void api
                                              .adminLawyerReview(
                                                p.user_id,
                                                false,
                                                "材料不完整",
                                              )
                                              .then(refresh)
                                              .catch((e) =>
                                                setError(
                                                  e instanceof Error ? e.message : "审核失败",
                                                ),
                                              )
                                          }
                                        >
                                          驳回
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                  {open && (
                                    <tr className="lw-detail-row">
                                      <td colSpan={8}>
                                        <div className="lawyer-detail">
                                          {renderLawyerMaterials(p)}
                                        </div>
                                      </td>
                                    </tr>
                                  )}
                                </Fragment>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      {selectedPending.length > 0 && (
                        <div className="ac-batch-bar sticky">
                          <span className="ac-batch-count">
                            已选 {selectedPending.length} 项
                          </span>
                          <button
                            type="button"
                            className="ac-btn-pass"
                            disabled={batchBusy}
                            onClick={() => void batchReview(true)}
                          >
                            批量通过
                          </button>
                          <button
                            type="button"
                            className="ac-btn-reject"
                            disabled={batchBusy}
                            onClick={() => void batchReview(false)}
                          >
                            批量驳回
                          </button>
                          <button
                            type="button"
                            className="lw-link"
                            onClick={() => setSelectedPending([])}
                          >
                            取消选择
                          </button>
                        </div>
                      )}
                      {renderListPager(
                        filteredPending.length,
                        pendingSafePage,
                        pendingPageCount,
                        setPendingPage,
                      )}
                    </>
                  )}
                </>
              ) : (
                <>
                  <p className="bk-hint">撤销后对方需重新提交认证材料。</p>
                  {renderListToolbar(
                    approvedSearch,
                    (v) => {
                      setApprovedSearch(v);
                      setApprovedPage(1);
                    },
                    approvedPageSize,
                    (n) => {
                      setApprovedPageSize(n);
                      setApprovedPage(1);
                    },
                    "搜索用户名 / ID / 职业 / 证号 / 地区…",
                  )}
                  {approvedLawyers.length === 0 ? (
                    <div className="bk-empty">暂无已通过认证</div>
                  ) : filteredApproved.length === 0 ? (
                    <div className="bk-empty">无匹配结果</div>
                  ) : (
                    <>
                      <div className="lw-table-wrap">
                        <table className="lw-table">
                          <thead>
                            <tr>
                              <th className="lw-col-user">从业者</th>
                              <th className="lw-col-prof">职业</th>
                              <th className="lw-col-license">证号</th>
                              <th className="lw-col-region">地区</th>
                              <th className="lw-col-spec">方向</th>
                              <th className="lw-col-time">审核时间</th>
                              <th className="lw-col-actions">操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pagedApproved.map((p) => {
                              const open = lawyerDetailId === p.user_id;
                              const specs = (p.specialties || []).join("、") || "—";
                              return (
                                <Fragment key={`ok-${p.user_id}`}>
                                  <tr className={open ? "is-open" : undefined}>
                                    <td className="lw-col-user">
                                      <div className="lw-user">
                                        <strong>{p.username || `用户#${p.user_id}`}</strong>
                                        <span>#{p.user_id}</span>
                                      </div>
                                    </td>
                                    <td className="lw-col-prof">
                                      <span className="lw-prof-badge">
                                        {PROF_LABEL[p.profession || "lawyer"] || "律师"}
                                      </span>
                                    </td>
                                    <td className="lw-col-license">
                                      <code>{p.license_no || "—"}</code>
                                    </td>
                                    <td className="lw-col-region">{p.region || "—"}</td>
                                    <td className="lw-col-spec" title={specs}>
                                      {specs}
                                    </td>
                                    <td className="lw-col-time">
                                      {p.reviewed_at
                                        ? String(p.reviewed_at).replace("T", " ").slice(0, 16)
                                        : "—"}
                                    </td>
                                    <td className="lw-col-actions">
                                      <div className="lw-ops">
                                        <button
                                          type="button"
                                          className="lw-link"
                                          onClick={() =>
                                            setLawyerDetailId(open ? null : p.user_id)
                                          }
                                        >
                                          {open ? "收起" : "资料"}
                                        </button>
                                        <button
                                          type="button"
                                          className="lw-link danger"
                                          onClick={() => void revokeLawyer(p)}
                                        >
                                          撤销
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                  {open && (
                                    <tr className="lw-detail-row">
                                      <td colSpan={7}>
                                        <div className="lawyer-detail">
                                          {renderLawyerMaterials(p)}
                                        </div>
                                      </td>
                                    </tr>
                                  )}
                                </Fragment>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      {renderListPager(
                        filteredApproved.length,
                        approvedSafePage,
                        approvedPageCount,
                        setApprovedPage,
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          )}

          {nav === "users" && can("users") && (
            <div className="admin-section ac-section-flush">
              {access?.is_root && (
                <p className="bk-hint">
                  点「设管理员」或「权限」可勾选后台板块；也可右键用户行打开同一弹窗。
                </p>
              )}
              <div className="ac-role-mix">
                <span>普通用户 {roleMix.user}</span>
                <span>律师 {roleMix.lawyer}</span>
                <span>法官 {roleMix.judge}</span>
                <span>检察官 {roleMix.prosecutor}</span>
                <span>管理员 {roleMix.admin}</span>
                <button
                  type="button"
                  className="ac-btn-ghost"
                  disabled={filteredUsers.length === 0}
                  onClick={exportUsersCsv}
                >
                  导出当前列表 CSV
                </button>
              </div>
              <div className="au-toolbar">
                <input
                  className="au-search"
                  placeholder="搜索用户名 / ID / 角色…"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                />
                <div className="au-filters">
                  {(
                    [
                      ["all", "全部"],
                      ["admin", "管理员"],
                      ["user", "普通用户"],
                      ["lawyer", "律师"],
                      ["judge", "法官"],
                      ["prosecutor", "检察官"],
                    ] as const
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      className={`au-chip ${roleFilter === key ? "active" : ""}`}
                      onClick={() => {
                        setRoleFilter(key);
                        setPage(1);
                      }}
                    >
                      {label}
                    </button>
                  ))}
                  <select
                    className="au-page-size"
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    aria-label="每页条数"
                  >
                    <option value={10}>每页 10</option>
                    <option value={20}>每页 20</option>
                    <option value={50}>每页 50</option>
                  </select>
                </div>
              </div>
              <div className="admin-users compact">
                {filteredUsers.length === 0 && (
                  <div className="bk-empty">{users.length === 0 ? "暂无用户" : "无匹配结果"}</div>
                )}
                {pagedUsers.map((u) => (
                  <div
                    className="admin-user compact"
                    key={u.id}
                    onContextMenu={(e) => openPermMenu(e, u)}
                  >
                    <div className="au-info">
                      <span className="au-name">
                        <span className="au-id">#{u.id}</span>
                        {u.username}
                        {u.is_root && <span className="admin-badge">根管理员</span>}
                        {u.role === "admin" && !u.is_root && (
                          <span className="admin-badge">管理员</span>
                        )}
                        {u.role === "lawyer" && <span className="admin-badge muted">律师</span>}
                        {u.role === "judge" && <span className="admin-badge muted">法官</span>}
                        {u.role === "prosecutor" && (
                          <span className="admin-badge muted">检察官</span>
                        )}
                      </span>
                      <span className="au-meta">
                        {u.session_count} 会话 · {u.message_count} 消息 · {u.created_at}
                      </span>
                      {u.role === "admin" && !u.is_root && (
                        <span className="perm-tags">
                          {(u.permissions || []).map((key) => (
                            <span className="perm-tag" key={key}>
                              {access?.catalog.find((c) => c.key === key)?.label || key}
                            </span>
                          ))}
                        </span>
                      )}
                    </div>
                    <div className="au-actions">
                      {u.is_root ? (
                        <span className="au-meta">不可改</span>
                      ) : access?.is_root && u.role === "admin" ? (
                        <>
                          <button
                            type="button"
                            className="btn-sm"
                            onClick={(e) => openPermMenu(e, u)}
                          >
                            权限
                          </button>
                          <button
                            type="button"
                            className="btn-sm btn-danger"
                            onClick={() => void revokeAdmin(u)}
                          >
                            撤销
                          </button>
                        </>
                      ) : (
                        <>
                          {u.role !== "admin" && access?.is_root && (
                            <button
                              type="button"
                              className="btn-sm"
                              onClick={(e) => openPermMenu(e, u)}
                            >
                              设管理员
                            </button>
                          )}
                          {u.role !== "admin" && (
                            <button
                              type="button"
                              className="btn-sm btn-danger"
                              onClick={() => void removeUser(u)}
                            >
                              删除
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {filteredUsers.length > 0 && (
                <div className="au-pager">
                  <button
                    type="button"
                    className="btn-sm"
                    disabled={safePage <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    上一页
                  </button>
                  <span className="au-pager-info">
                    第 {safePage} / {pageCount} 页 · 共 {filteredUsers.length} 人
                  </span>
                  <button
                    type="button"
                    className="btn-sm"
                    disabled={safePage >= pageCount}
                    onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                  >
                    下一页
                  </button>
                </div>
              )}
            </div>
          )}

          {nav === "kb" && can("kb") && <KnowledgeBasePanel />}

          {nav === "feedbacks" && can("feedbacks") && (
            <div className="admin-section ac-section-flush">
              <div className="fb-kpi-row">
                <div className="fb-kpi">
                  <span>反馈总数</span>
                  <strong>{fbStats.total}</strong>
                </div>
                <div className="fb-kpi ok">
                  <span>有用</span>
                  <strong>{fbStats.useful}</strong>
                </div>
                <div className="fb-kpi bad">
                  <span>无用</span>
                  <strong>{fbStats.useless}</strong>
                </div>
                <div className="fb-kpi rate">
                  <span>有用率</span>
                  <strong>{usefulRate == null ? "—" : `${usefulRate}%`}</strong>
                  {fbStats.total > 0 && (
                    <div className="ac-quality-bar" aria-hidden>
                      <i style={{ width: `${usefulRate ?? 0}%` }} />
                    </div>
                  )}
                </div>
              </div>

              <div className="ac-fb-head">
                <p className="bk-hint" style={{ marginBottom: 0 }}>
                  当前列表 {filteredFeedbacks.length} 条
                </p>
                <div className="ac-subtabs">
                  {(
                    [
                      ["all", "全部"],
                      ["useful", "有用"],
                      ["useless", "无用"],
                    ] as const
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      className={fbFilter === key ? "active" : ""}
                      onClick={() => setFbFilter(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <p className="bk-hint">
                有用/无用都要点开看完整问答，才能判断模型答得对不对、用户为何这样评。
              </p>

              {filteredFeedbacks.length === 0 ? (
                <div className="bk-empty">暂无反馈</div>
              ) : (
                <div className="lw-table-wrap">
                  <table className="lw-table fb-table">
                    <thead>
                      <tr>
                        <th className="fb-col-rating">评价</th>
                        <th className="fb-col-user">用户</th>
                        <th className="fb-col-q">用户提问</th>
                        <th className="fb-col-preview">回答摘要</th>
                        <th className="fb-col-comment">备注</th>
                        <th className="fb-col-time">时间</th>
                        <th className="fb-col-actions">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFeedbacks.map((f) => {
                        const useful = f.rating === "useful";
                        const open = fbOpenId === f.id;
                        const when = String(f.created_at || "")
                          .replace("T", " ")
                          .slice(0, 16);
                        const qPreview = (f.question_preview || "").trim() || "—";
                        const preview = (f.message_preview || "").trim() || "—";
                        const comment = (f.comment || "").trim();
                        return (
                          <Fragment key={f.id}>
                            <tr className={open ? "is-open" : undefined}>
                              <td className="fb-col-rating">
                                <span className={`fb-tag ${useful ? "ok" : "bad"}`}>
                                  {useful ? "有用" : "无用"}
                                </span>
                              </td>
                              <td className="fb-col-user">
                                <div className="lw-user">
                                  <strong title={f.username}>{f.username || "—"}</strong>
                                  <span>#{f.user_id}</span>
                                </div>
                              </td>
                              <td className="fb-col-q" title={qPreview}>
                                {qPreview}
                              </td>
                              <td className="fb-col-preview" title={preview}>
                                {preview}
                              </td>
                              <td className="fb-col-comment" title={comment || undefined}>
                                {comment || <span className="fb-muted">—</span>}
                              </td>
                              <td className="fb-col-time">{when || "—"}</td>
                              <td className="fb-col-actions">
                                <button
                                  type="button"
                                  className="lw-link"
                                  onClick={() => void toggleFeedbackDetail(f.id)}
                                >
                                  {open ? "收起" : "看全文"}
                                </button>
                              </td>
                            </tr>
                            {open && (
                              <tr className="lw-detail-row">
                                <td colSpan={7}>
                                  <div className="fb-detail">
                                    {fbDetailLoading || !fbDetail ? (
                                      <p className="fb-muted">加载问答上下文…</p>
                                    ) : (
                                      <>
                                        <div className="fb-detail-meta">
                                          <span className={`fb-tag ${useful ? "ok" : "bad"}`}>
                                            {useful ? "有用" : "无用"}
                                          </span>
                                          <span>消息 #{fbDetail.message_id}</span>
                                          <span>会话 {fbDetail.session_id || "—"}</span>
                                        </div>
                                        <section className="fb-block">
                                          <h4>用户提问</h4>
                                          <pre>{fbDetail.question || "（未找到提问）"}</pre>
                                        </section>
                                        <section className="fb-block">
                                          <h4>助手回答</h4>
                                          <pre>{fbDetail.answer || "（无内容）"}</pre>
                                        </section>
                                        <section className="fb-block">
                                          <h4>用户备注</h4>
                                          <pre>
                                            {(fbDetail.comment || "").trim() || "（未填写）"}
                                          </pre>
                                        </section>
                                      </>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {nav === "ops" && (
            <>
              {opsSub === "status" && can("status") && status && (
                <div className="admin-section ac-section-flush">
                  <div className="admin-status ac-status-rich">
                    <div>
                      <span>对话模型</span>
                      {status.chat_model}
                    </div>
                    <div>
                      <span>嵌入模型</span>
                      {status.embedding_model}（{status.embedding_dim} 维）
                    </div>
                    <div>
                      <span>OCR</span>
                      <em className={status.ocr_enabled ? "ok" : "off"}>
                        {status.ocr_enabled ? "已启用" : "已关闭"}
                      </em>
                    </div>
                    <div>
                      <span>法规时效</span>
                      <em className={status.effective_status_enabled ? "ok" : "off"}>
                        {status.effective_status_enabled ? "已启用" : "已关闭"}
                      </em>
                    </div>
                    <div>
                      <span>向量库</span>
                      {status.vector_store}
                    </div>
                    <div>
                      <span>知识库源</span>
                      {status.kb_source}
                    </div>
                  </div>
                </div>
              )}
              {opsSub === "backups" && can("backups") && <BackupPanel />}
              {opsSub === "logs" && can("logs") && <LogsPanel />}
            </>
          )}
        </div>
      </div>

      {menu &&
        access?.is_root &&
        createPortal(
          <div
            className="perm-modal-backdrop"
            role="presentation"
            onClick={() => setMenu(null)}
          >
            <div
              className="perm-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="perm-modal-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h4 id="perm-modal-title">
                {menu.user.role === "admin"
                  ? `调整「${menu.user.username}」的权限`
                  : `设「${menu.user.username}」为管理员`}
              </h4>
              <p className="bk-hint">请至少勾选一项可管理的后台板块。</p>
              <div className="perm-modal-list">
                {access.catalog.map((item) => (
                  <label key={item.key}>
                    <input
                      type="checkbox"
                      checked={menu.picked.includes(item.key)}
                      onChange={(e) =>
                        setMenu((cur) =>
                          cur
                            ? {
                                ...cur,
                                picked: e.target.checked
                                  ? [...cur.picked, item.key]
                                  : cur.picked.filter((k) => k !== item.key),
                              }
                            : cur,
                        )
                      }
                    />
                    {item.label}
                  </label>
                ))}
              </div>
              <div className="ctx-actions">
                <button
                  type="button"
                  className="btn-sm"
                  onClick={() => void setRole(menu.user, "admin", menu.picked)}
                >
                  {menu.user.role === "admin" ? "保存权限" : "设为管理员"}
                </button>
                {menu.user.role === "admin" && (
                  <button
                    type="button"
                    className="btn-sm btn-danger"
                    onClick={() => void revokeAdmin(menu.user)}
                  >
                    撤销管理员
                  </button>
                )}
                <button type="button" className="btn-sm" onClick={() => setMenu(null)}>
                  关闭
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}

function KnowledgeBasePanel() {
  const { documents, loading, uploading, error, refresh, upload, remove } = useDocuments();
  const [toast, setToast] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await upload(file);
    setToast(res.message);
    setTimeout(() => setToast(null), 4000);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="admin-section ac-section-flush">
      <div className="log-head">
        <h3>知识库文档（{documents.length}）</h3>
        <button className="btn-ghost btn-sm" onClick={() => void refresh()} disabled={loading}>
          {loading ? "刷新中…" : "刷新"}
        </button>
      </div>
      <p className="bk-hint">支持 docx / pdf / txt / md；扫描件自动 OCR。入库后可用于问答与法规检索。</p>
      <input
        ref={fileRef}
        type="file"
        accept=".docx,.pdf,.txt,.md"
        hidden
        onChange={(e) => void onFile(e)}
      />
      <div className="bk-create">
        <button
          className="btn-primary btn-sm"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? "上传解析中…" : "上传文档"}
        </button>
      </div>
      {toast && <div className="bk-msg">{toast}</div>}
      {error && <div className="err-text">{error}</div>}
      <div className="admin-users" style={{ marginTop: 12 }}>
        {documents.length === 0 && !loading && <div className="bk-empty">暂无文档</div>}
        {documents.slice(0, 300).map((d) => (
          <div className="admin-user" key={d.doc_id}>
            <div className="au-info">
              <span className="au-name">{d.title}</span>
              <span className="au-meta">
                {d.category || "未分类"} · {d.chunks} 块
                {d.effective_status ? ` · ${d.effective_status}` : ""}
              </span>
            </div>
            <div className="au-actions">
              <button
                className="btn-sm btn-danger"
                onClick={() => {
                  if (confirm(`确定从知识库删除「${d.title}」？`)) void remove(d.doc_id);
                }}
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BackupPanel() {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([]);
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [msgType, setMsgType] = useState<"ok" | "err">("ok");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const refresh = useCallback(async () => {
    try {
      const r = await api.backupList();
      setSnapshots(r.snapshots);
    } catch (err) {
      setMsgType("err");
      setMsg(err instanceof Error ? err.message : "加载失败");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const s = await api.backupCreate(desc.trim());
      setMsgType("ok");
      setMsg(`已创建备份「${s.description || s.name}」（${s.size_mb} MB）`);
      setDesc("");
      setPage(1);
      await refresh();
    } catch (err) {
      setMsgType("err");
      setMsg(err instanceof Error ? err.message : "创建失败");
    } finally {
      setBusy(false);
    }
  };

  const restore = async (s: SnapshotItem) => {
    if (
      !confirm(
        `确定恢复到「${s.description || s.name}」？\n当前数据会被覆盖，建议先再创建一份备份作为保险。`,
      )
    )
      return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.backupRestore(s.name);
      setMsgType("ok");
      setMsg(`已恢复该备份（还原 ${r.count} 个文件）`);
      await refresh();
    } catch (err) {
      setMsgType("err");
      setMsg(err instanceof Error ? err.message : "恢复失败");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (s: SnapshotItem) => {
    if (!confirm(`确定删除备份「${s.description || s.name}」？此操作不可撤销。`)) return;
    try {
      await api.backupDelete(s.name);
      setMsgType("ok");
      setMsg(`已删除备份「${s.description || s.name}」`);
      await refresh();
    } catch (err) {
      setMsgType("err");
      setMsg(err instanceof Error ? err.message : "删除失败");
    }
  };

  const fmtTime = (t: string) => {
    if (!t) return "";
    try {
      const d = new Date(
        t.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, "$1-$2-$3T$4:$5:$6"),
      );
      return isNaN(d.getTime()) ? t : d.toLocaleString("zh-CN");
    } catch {
      return t;
    }
  };

  const sq = search.trim().toLowerCase();
  const filtered = snapshots.filter((s) => {
    if (!sq) return true;
    return (
      (s.description || "").toLowerCase().includes(sq) ||
      (s.name || "").toLowerCase().includes(sq) ||
      fmtTime(s.created_at).toLowerCase().includes(sq)
    );
  });
  const { pageCount, safePage, slice: paged } = paginate(filtered, page, pageSize);
  const totalMb = snapshots.reduce((sum, s) => sum + (Number(s.size_mb) || 0), 0);

  return (
    <div className="admin-section bk-panel ac-section-flush">
      <div className="bk-head">
        <div>
          <h3>数据备份</h3>
          <p className="bk-sub">备份用户、会话与知识库等运行数据。代码发版请用 Git。</p>
        </div>
        <button type="button" className="btn-ghost btn-sm" onClick={() => void refresh()} disabled={busy}>
          刷新
        </button>
      </div>

      <div className="bk-coverage">
        <span className="bk-chip">用户账号</span>
        <span className="bk-chip">会话消息</span>
        <span className="bk-chip">知识库索引</span>
        <span className="bk-chip muted">代码 → Git</span>
      </div>

      <div className="bk-create-card">
        <div className="bk-create-label">
          <strong>新建数据备份</strong>
          <span>上线、大批量入库或清库前建议先备份</span>
        </div>
        <div className="bk-create">
          <input
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !busy) void create();
            }}
            placeholder="说明（可选）：如上线前、测评数据备份…"
            className="bk-input"
            disabled={busy}
          />
          <button
            type="button"
            className="btn-primary btn-sm bk-create-btn"
            onClick={() => void create()}
            disabled={busy}
          >
            {busy ? "处理中…" : "创建备份"}
          </button>
        </div>
      </div>

      {msg && <div className={`bk-msg ${msgType === "err" ? "err" : ""}`}>{msg}</div>}

      <div className="bk-list-head">
        <div className="bk-list-title">
          已有备份
          <span className="bk-count">
            {filtered.length}/{snapshots.length}
            {snapshots.length > 0 ? ` · 共 ${totalMb.toFixed(1)} MB` : ""}
          </span>
        </div>
        {snapshots.length > 0 && (
          <div className="au-toolbar bk-toolbar">
            <input
              className="au-search"
              placeholder="搜索说明 / 文件名 / 时间…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
            <div className="au-filters">
              <select
                className="au-page-size"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                aria-label="每页条数"
              >
                <option value={10}>每页 10</option>
                <option value={20}>每页 20</option>
                <option value={50}>每页 50</option>
              </select>
            </div>
          </div>
        )}
      </div>

      <div className="bk-list">
        {snapshots.length === 0 ? (
          <div className="bk-empty-state">
            <div className="bk-empty-icon" aria-hidden>
              ◎
            </div>
            <div className="bk-empty-title">还没有数据备份</div>
            <div className="bk-empty-desc">
              这里只备份运行数据。功能代码请用 Git 提交；恢复备份会覆盖当前业务数据。
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bk-empty">无匹配备份</div>
        ) : (
          paged.map((s, idx) => (
            <div className="bk-item" key={s.name}>
              <div className="bk-index" aria-hidden>
                {String((safePage - 1) * pageSize + idx + 1).padStart(2, "0")}
              </div>
              <div className="bk-info">
                <div className="bk-name-row">
                  <div className="bk-name">{s.description || s.name}</div>
                  {!s.description && <span className="bk-tag">未命名</span>}
                  {idx === 0 && safePage === 1 && <span className="bk-tag latest">最近</span>}
                </div>
                <div className="bk-meta">
                  <span>{fmtTime(s.created_at) || "时间未知"}</span>
                  <span className="bk-dot">·</span>
                  <span className="bk-size">{s.size_mb} MB</span>
                  <span className="bk-dot">·</span>
                  <span className="bk-id" title={s.name}>
                    {s.name}
                  </span>
                </div>
              </div>
              <div className="bk-actions">
                <button
                  type="button"
                  className="btn-sm bk-restore"
                  disabled={busy}
                  onClick={() => void restore(s)}
                >
                  恢复
                </button>
                <button
                  type="button"
                  className="btn-sm btn-danger"
                  disabled={busy}
                  onClick={() => void remove(s)}
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {filtered.length > 0 && (
        <div className="au-pager">
          <button
            type="button"
            className="btn-sm"
            disabled={safePage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span className="au-pager-info">
            第 {safePage} / {pageCount} 页 · 共 {filtered.length} 个
          </span>
          <button
            type="button"
            className="btn-sm"
            disabled={safePage >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
          >
            下一页
          </button>
        </div>
      )}

      <p className="bk-foot">恢复会覆盖当前业务数据；删除备份后无法找回。代码回退请用 Git。</p>
    </div>
  );
}

function LogsPanel() {
  const [logs, setLogs] = useState<AdminLogItem[]>([]);

  const refresh = useCallback(async () => {
    try {
      const r = await api.adminLogs(100);
      setLogs(r.logs);
    } catch {
      /* 忽略 */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const actionLabel: Record<string, string> = {
    delete_user: "删除用户",
    set_role: "修改角色",
    backup_create: "创建数据备份",
    backup_restore: "恢复数据备份",
    backup_delete: "删除数据备份",
    kb_upload: "上传文档",
    kb_delete: "删除文档",
    kb_ingest: "批量入库",
    lawyer_review: "律师审核",
    lawyer_revoke: "撤销律师认证",
  };

  return (
    <div className="admin-section ac-section-flush">
      <div className="log-head">
        <h3>操作日志</h3>
        <button className="btn-ghost btn-sm" onClick={refresh}>
          刷新
        </button>
      </div>
      <div className="log-list">
        {logs.length === 0 && <div className="bk-empty">暂无操作记录</div>}
        {logs.map((l) => (
          <div className="log-item" key={l.id}>
            <span className="log-action">{actionLabel[l.action] || l.action}</span>
            <span className="log-detail">{l.detail}</span>
            <span className="log-meta">
              {l.actor_name} · {l.created_at}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
