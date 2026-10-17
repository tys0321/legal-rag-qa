// 管理后台视图（仅 admin 可见）：用户管理 + 系统统计 + 系统状态

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type MouseEvent,
} from "react";
import { createPortal } from "react-dom";
import { api } from "../api/client";
import { useDocuments } from "../hooks/useDocuments";
import type {
  AdminAccess,
  AdminLogItem,
  AdminStats,
  AdminUserItem,
  FeedbackItem,
  LawyerProfile,
  SnapshotItem,
  SystemStatus,
} from "../api/types";

type PermMenu = { user: AdminUserItem; picked: string[] };

function matchLawyer(p: LawyerProfile, q: string): boolean {
  if (!q) return true;
  const hay = [
    p.username || "",
    String(p.user_id),
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

export default function AdminPanel() {
  const [access, setAccess] = useState<AdminAccess | null>(null);
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [pendingLawyers, setPendingLawyers] = useState<LawyerProfile[]>([]);
  const [approvedLawyers, setApprovedLawyers] = useState<LawyerProfile[]>([]);
  const [lawyerDetailId, setLawyerDetailId] = useState<number | null>(null);
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [fbStats, setFbStats] = useState({ total: 0, useful: 0, useless: 0 });
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | "admin" | "user" | "lawyer">("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pendingSearch, setPendingSearch] = useState("");
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingPageSize, setPendingPageSize] = useState(10);
  const [approvedSearch, setApprovedSearch] = useState("");
  const [approvedPage, setApprovedPage] = useState(1);
  const [approvedPageSize, setApprovedPageSize] = useState(10);
  const [menu, setMenu] = useState<PermMenu | null>(null);

  const can = useCallback(
    (key: string) => !!access && (access.is_root || access.permissions.includes(key)),
    [access],
  );

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const acc = await api.adminAccess();
      setAccess(acc);
      const allow = (key: string) => acc.is_root || acc.permissions.includes(key);
      const [u, s, st, lw, ap, fb] = await Promise.all([
        allow("users") ? api.adminUsers() : Promise.resolve({ users: [] as AdminUserItem[] }),
        allow("stats") ? api.adminStats() : Promise.resolve(null),
        allow("status") ? api.adminStatus() : Promise.resolve(null),
        allow("lawyers")
          ? api.adminLawyerPending().catch(() => ({ items: [] as LawyerProfile[] }))
          : Promise.resolve({ items: [] as LawyerProfile[] }),
        allow("lawyers")
          ? api.adminLawyerApproved().catch(() => ({ items: [] as LawyerProfile[] }))
          : Promise.resolve({ items: [] as LawyerProfile[] }),
        allow("feedbacks")
          ? api.adminFeedbacks(50).catch(() => ({ total: 0, useful: 0, useless: 0, items: [] as FeedbackItem[] }))
          : Promise.resolve({ total: 0, useful: 0, useless: 0, items: [] as FeedbackItem[] }),
      ]);
      setUsers(u.users);
      setStats(s);
      setStatus(st);
      setPendingLawyers(lw.items || []);
      setApprovedLawyers(ap.items || []);
      setFeedbacks(fb.items || []);
      setFbStats({ total: fb.total, useful: fb.useful, useless: fb.useless });
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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

  // 用户搜索 + 角色过滤 + 分页
  const q = search.trim().toLowerCase();
  const filteredUsers = users.filter((u) => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false;
    if (!q) return true;
    return (
      u.username.toLowerCase().includes(q) ||
      String(u.id).includes(q) ||
      u.role.includes(q)
    );
  });
  const { pageCount, safePage, slice: pagedUsers } = paginate(filteredUsers, page, pageSize);

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

  return (
    <div className="admin-panel">
      <div className="admin-head">
        <h2>🛡️ 管理后台</h2>
        <button className="btn-ghost btn-sm" onClick={refresh}>
          刷新
        </button>
      </div>
      {error && <div className="err-text">{error}</div>}

      {can("stats") && stats && (
        <div className="admin-stats">
          <div className="stat-card">
            <div className="stat-num">{stats.user_count}</div>
            <div className="stat-label">用户</div>
          </div>
          <div className="stat-card">
            <div className="stat-num">{stats.session_count}</div>
            <div className="stat-label">会话</div>
          </div>
          <div className="stat-card">
            <div className="stat-num">{stats.message_count}</div>
            <div className="stat-label">消息</div>
          </div>
          <div className="stat-card">
            <div className="stat-num">{stats.doc_count}</div>
            <div className="stat-label">文档</div>
          </div>
          <div className="stat-card">
            <div className="stat-num">{stats.chunk_count}</div>
            <div className="stat-label">检索块</div>
          </div>
        </div>
      )}

      {can("lawyers") && (
      <>
      <div className="admin-section">
        <h3>⚖️ 律师认证待审（{filteredPending.length}/{pendingLawyers.length}）</h3>
        <p className="bk-hint">点「资料」展开证号与执业证附件；无附件多为演示/仅文本申请。</p>
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
          "🔍 搜索用户名 / ID / 证号 / 地区 / 擅长…",
        )}
        {pendingLawyers.length === 0 ? (
          <div className="bk-empty">暂无待审申请</div>
        ) : (
          <>
            <div className="admin-users">
              {filteredPending.length === 0 && <div className="bk-empty">无匹配结果</div>}
              {pagedPending.map((p) => {
                const open = lawyerDetailId === p.user_id;
                const fileCount = (p.license_files || []).length;
                return (
                <div className="admin-user lawyer-row" key={p.user_id}>
                  <div className="au-info">
                    <span className="au-name">
                      <span className="au-id">#{p.user_id}</span>
                      {p.username || `用户#${p.user_id}`}
                      <span className="admin-badge">待审</span>
                      <span className="perm-tag">{fileCount ? `${fileCount} 份材料` : "无附件"}</span>
                    </span>
                    <span className="au-meta">
                      证号 {p.license_no} · {p.region} · {(p.specialties || []).join("、") || "未填擅长"}
                    </span>
                    {open && (
                      <div className="lawyer-detail">
                        <div className="au-meta">用户 ID #{p.user_id}</div>
                        {renderLawyerMaterials(p)}
                      </div>
                    )}
                  </div>
                  <div className="au-actions">
                    <button
                      type="button"
                      className="btn-sm"
                      onClick={() => setLawyerDetailId(open ? null : p.user_id)}
                    >
                      {open ? "收起" : "资料"}
                    </button>
                    <button
                      type="button"
                      className="btn-sm"
                      onClick={() =>
                        void api.adminLawyerReview(p.user_id, true).then(refresh).catch((e) =>
                          setError(e instanceof Error ? e.message : "审核失败"),
                        )
                      }
                    >
                      通过
                    </button>
                    <button
                      type="button"
                      className="btn-sm btn-danger"
                      onClick={() =>
                        void api
                          .adminLawyerReview(p.user_id, false, "材料不完整")
                          .then(refresh)
                          .catch((e) => setError(e instanceof Error ? e.message : "审核失败"))
                      }
                    >
                      驳回
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
            {renderListPager(filteredPending.length, pendingSafePage, pendingPageCount, setPendingPage)}
          </>
        )}
      </div>

      <div className="admin-section">
        <h3>✅ 已通过律师（{filteredApproved.length}/{approvedLawyers.length}）</h3>
        <p className="bk-hint">可通过「撤销」收回律师认证；撤销后对方需重新申请。</p>
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
          "🔍 搜索用户名 / ID / 证号 / 地区 / 擅长…",
        )}
        {approvedLawyers.length === 0 ? (
          <div className="bk-empty">暂无已通过律师</div>
        ) : (
          <>
            <div className="admin-users">
              {filteredApproved.length === 0 && <div className="bk-empty">无匹配结果</div>}
              {pagedApproved.map((p) => {
                const open = lawyerDetailId === p.user_id;
                return (
                  <div className="admin-user lawyer-row" key={`ok-${p.user_id}`}>
                    <div className="au-info">
                      <span className="au-name">
                        <span className="au-id">#{p.user_id}</span>
                        {p.username || `用户#${p.user_id}`}
                        <span className="admin-badge">已通过</span>
                      </span>
                      <span className="au-meta">
                        证号 {p.license_no} · {p.region} · {(p.specialties || []).join("、") || "未填"}
                        {p.reviewed_at ? ` · 审核于 ${p.reviewed_at}` : ""}
                      </span>
                      {open && (
                        <div className="lawyer-detail">
                          {renderLawyerMaterials(p)}
                        </div>
                      )}
                    </div>
                    <div className="au-actions">
                      <button
                        type="button"
                        className="btn-sm"
                        onClick={() => setLawyerDetailId(open ? null : p.user_id)}
                      >
                        {open ? "收起" : "资料"}
                      </button>
                      <button
                        type="button"
                        className="btn-sm btn-danger"
                        onClick={() => void revokeLawyer(p)}
                      >
                        撤销
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            {renderListPager(filteredApproved.length, approvedSafePage, approvedPageCount, setApprovedPage)}
          </>
        )}
      </div>
      </>
      )}

      {can("users") && (
      <div className="admin-section">
        <h3>👥 用户列表（{filteredUsers.length}/{users.length}）</h3>
        {access?.is_root && (
          <p className="bk-hint">
            点「设管理员」或「权限」可勾选后台板块；已是管理员的可点「撤销」收回。也可右键用户行打开同一弹窗。
          </p>
        )}
        <div className="au-toolbar">
          <input
            className="au-search"
            placeholder="🔍 搜索用户名 / ID / 角色…"
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
                  {u.role === "admin" && !u.is_root && <span className="admin-badge">管理员</span>}
                  {u.role === "lawyer" && <span className="admin-badge muted">律师</span>}
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
                    <button type="button" className="btn-sm" onClick={(e) => openPermMenu(e, u)}>
                      权限
                    </button>
                    <button type="button" className="btn-sm btn-danger" onClick={() => void revokeAdmin(u)}>
                      撤销
                    </button>
                  </>
                ) : (
                  <>
                    {u.role !== "admin" && access?.is_root && (
                      <button type="button" className="btn-sm" onClick={(e) => openPermMenu(e, u)}>
                        设管理员
                      </button>
                    )}
                    {u.role !== "admin" && (
                      <button type="button" className="btn-sm btn-danger" onClick={() => void removeUser(u)}>
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

      {can("status") && status && (
        <div className="admin-section">
          <h3>⚙️ 系统状态</h3>
          <div className="admin-status">
            <div><span>对话模型</span>{status.chat_model}</div>
            <div><span>嵌入模型</span>{status.embedding_model}（{status.embedding_dim} 维）</div>
            <div><span>OCR</span>{status.ocr_enabled ? "已启用" : "已关闭"}</div>
            <div><span>法规时效</span>{status.effective_status_enabled ? "已启用" : "已关闭"}</div>
            <div><span>向量库</span>{status.vector_store}</div>
            <div><span>知识库源</span>{status.kb_source}</div>
          </div>
        </div>
      )}

      {can("feedbacks") && (
      <div className="admin-section">
        <h3>
          💬 消息反馈（{fbStats.total} · 有用 {fbStats.useful} / 无用 {fbStats.useless}）
        </h3>
        {feedbacks.length === 0 ? (
          <div className="bk-empty">暂无反馈</div>
        ) : (
          <div className="admin-users">
            {feedbacks.map((f) => (
              <div className="admin-user" key={f.id}>
                <div className="au-info">
                  <span className="au-name">
                    {f.username}
                    <span className={`admin-badge ${f.rating === "useful" ? "" : "danger"}`}>
                      {f.rating === "useful" ? "有用" : "无用"}
                    </span>
                  </span>
                  <span className="au-meta">
                    msg#{f.message_id} · {f.created_at}
                    {f.comment ? ` · ${f.comment}` : ""}
                  </span>
                  <span className="au-meta">{f.message_preview}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {can("kb") && <KnowledgeBasePanel />}

      {can("backups") && <BackupPanel />}

      {can("logs") && <LogsPanel />}
    </div>
  );
}

/** 知识库：上传 / 列表 / 删除（仅后台） */
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
    <div className="admin-section">
      <div className="log-head">
        <h3>📚 知识库（{documents.length}）</h3>
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
          {uploading ? "上传解析中…" : "⬆ 上传文档"}
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

/** 业务数据备份：创建 / 列表 / 恢复 / 删除（代码版本请用 Git） */
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
      setMsg(`已恢复到该版本（还原 ${r.count} 个文件）`);
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
      const d = new Date(t.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, "$1-$2-$3T$4:$5:$6"));
      return isNaN(d.getTime()) ? t : d.toLocaleString("zh-CN");
    } catch {
      return t;
    }
  };

  const q = search.trim().toLowerCase();
  const filtered = snapshots.filter((s) => {
    if (!q) return true;
    return (
      (s.description || "").toLowerCase().includes(q) ||
      (s.name || "").toLowerCase().includes(q) ||
      fmtTime(s.created_at).toLowerCase().includes(q)
    );
  });
  const { pageCount, safePage, slice: paged } = paginate(filtered, page, pageSize);
  const totalMb = snapshots.reduce((sum, s) => sum + (Number(s.size_mb) || 0), 0);

  return (
    <div className="admin-section bk-panel">
      <div className="bk-head">
        <div>
          <h3>数据备份</h3>
          <p className="bk-sub">备份用户、会话与知识库等运行数据。代码发版请用 Git（本仓库已对接 GitHub）。</p>
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
          <button type="button" className="btn-primary btn-sm bk-create-btn" onClick={() => void create()} disabled={busy}>
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
              placeholder="🔍 搜索说明 / 文件名 / 时间…"
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
              这里只备份运行数据。功能代码请用 Git 提交到 GitHub；恢复备份会覆盖当前业务数据。
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
                <button type="button" className="btn-sm bk-restore" disabled={busy} onClick={() => void restore(s)}>
                  恢复
                </button>
                <button type="button" className="btn-sm btn-danger" disabled={busy} onClick={() => void remove(s)}>
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

/** 操作日志：追踪管理操作（删用户/改角色/快照等） */
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
    delete_user: "🗑 删除用户",
    set_role: "🔑 修改角色",
    backup_create: "💾 创建数据备份",
    backup_restore: "↩️ 恢复数据备份",
    backup_delete: "❌ 删除数据备份",
    kb_upload: "📚 上传文档",
    kb_delete: "📚 删除文档",
    kb_ingest: "📚 批量入库",
    lawyer_review: "⚖️ 律师审核",
    lawyer_revoke: "↩️ 撤销律师认证",
  };

  return (
    <div className="admin-section">
      <div className="log-head">
        <h3>📜 操作日志</h3>
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
