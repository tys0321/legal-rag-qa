// 管理后台视图（仅 admin 可见）：用户管理 + 系统统计 + 系统状态

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AdminLogItem, AdminStats, AdminUserItem, SnapshotItem, SystemStatus } from "../api/types";

export default function AdminPanel() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [u, s, st] = await Promise.all([
        api.adminUsers(),
        api.adminStats(),
        api.adminStatus(),
      ]);
      setUsers(u.users);
      setStats(s);
      setStatus(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setRole = async (user: AdminUserItem, role: string) => {
    try {
      await api.adminSetRole(user.id, role);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
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

  // 用户搜索过滤
  const q = search.trim().toLowerCase();
  const filteredUsers = q
    ? users.filter(
        (u) =>
          u.username.toLowerCase().includes(q) ||
          String(u.id).includes(q) ||
          u.role.includes(q),
      )
    : users;

  return (
    <div className="admin-panel">
      <div className="admin-head">
        <h2>🛡️ 管理后台</h2>
        <button className="btn-ghost btn-sm" onClick={refresh}>
          刷新
        </button>
      </div>
      {error && <div className="err-text">{error}</div>}

      {stats && (
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

      <div className="admin-section">
        <h3>👥 用户列表（{users.length}）</h3>
        <input
          className="au-search"
          placeholder="🔍 搜索用户名 / ID / 角色…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="admin-users">
          {filteredUsers.length === 0 && (
            <div className="bk-empty">{users.length === 0 ? "暂无用户" : "无匹配结果"}</div>
          )}
          {filteredUsers.map((u) => (
            <div className="admin-user" key={u.id}>
              <div className="au-info">
                <span className="au-name">
                  {u.username}
                  {u.role === "admin" && <span className="admin-badge">管理员</span>}
                </span>
                <span className="au-meta">
                  {u.session_count} 会话 · {u.message_count} 消息 · 注册于 {u.created_at}
                </span>
              </div>
              <div className="au-actions">
                {u.role !== "admin" ? (
                  <button className="btn-sm" onClick={() => void setRole(u, "admin")}>
                    设为管理员
                  </button>
                ) : (
                  <button className="btn-sm" onClick={() => void setRole(u, "user")}>
                    取消管理
                  </button>
                )}
                <button className="btn-sm btn-danger" onClick={() => void removeUser(u)}>
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {status && (
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

      <BackupPanel />

      <LogsPanel />
    </div>
  );
}

/** 版本快照管理：创建 / 列表 / 恢复 / 删除（无需 git） */
function BackupPanel() {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([]);
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await api.backupList();
      setSnapshots(r.snapshots);
    } catch (err) {
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
      setMsg(`✅ 已创建快照（${s.size_mb} MB）`);
      setDesc("");
      await refresh();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "创建失败");
    } finally {
      setBusy(false);
    }
  };

  const restore = async (s: SnapshotItem) => {
    if (!confirm(`确定恢复到「${s.description || s.name}」？\n当前数据会被覆盖，建议先创建一个新快照。`)) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.backupRestore(s.name);
      setMsg(`✅ 已恢复到该版本（还原 ${r.count} 个文件）`);
      await refresh();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "恢复失败");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (s: SnapshotItem) => {
    if (!confirm(`确定删除快照「${s.description || s.name}」？`)) return;
    try {
      await api.backupDelete(s.name);
      await refresh();
    } catch (err) {
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

  return (
    <div className="admin-section">
      <h3>🕐 版本管理（快照）</h3>
      <p className="bk-hint">
        像游戏存档一样备份与恢复整个系统（用户、会话、知识库索引）。无需任何 git 命令。
      </p>
      <div className="bk-create">
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="快照说明（可选，如：上线前 / 大改动前）"
          className="bk-input"
        />
        <button className="btn-primary btn-sm" onClick={create} disabled={busy}>
          {busy ? "处理中…" : "＋ 创建快照"}
        </button>
      </div>
      {msg && <div className="bk-msg">{msg}</div>}
      <div className="bk-list">
        {snapshots.length === 0 && <div className="bk-empty">暂无快照，点上方按钮创建</div>}
        {snapshots.map((s) => (
          <div className="bk-item" key={s.name}>
            <div className="bk-info">
              <div className="bk-name">{s.description || s.name}</div>
              <div className="bk-meta">
                {fmtTime(s.created_at)} · {s.size_mb} MB
              </div>
            </div>
            <div className="bk-actions">
              <button className="btn-sm bk-restore" onClick={() => void restore(s)}>
                恢复此版本
              </button>
              <button className="btn-sm btn-danger" onClick={() => void remove(s)}>
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
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
    backup_create: "🕐 创建快照",
    backup_restore: "↩️ 恢复快照",
    backup_delete: "❌ 删除快照",
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
