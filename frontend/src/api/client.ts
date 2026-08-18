// API 客户端：封装与后端的所有交互（带鉴权 token）

import type {
  AdminLogItem,
  AdminStats,
  AdminUserItem,
  AuthResponse,
  ChatRequest,
  ChatResponse,
  ChatMessage,
  DocumentItem,
  SessionItem,
  SnapshotItem,
  StatsResponse,
  SystemStatus,
  UploadResponse,
  UserInfo,
} from "./types";

const BASE = ""; // 同源部署（后端托管构建产物）或 Vite dev 代理

const TOKEN_KEY = "legal_rag_token";
const USER_KEY = "legal_rag_user";

export const tokenStore = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  user(): { username: string; user_id: number; role?: string } | null {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  saveUser(u: { username: string; user_id: number; role?: string }): void {
    localStorage.setItem(USER_KEY, JSON.stringify(u));
  },
  isAdmin(): boolean {
    return this.user()?.role === "admin";
  },
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) };
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const token = tokenStore.get();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    const msg = "网络连接失败，请检查服务是否运行";
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message: msg, type: "error" } }));
    throw new Error(msg);
  }
  if (resp.status === 401) {
    // 登录失效：清理本地态，触发重新登录
    tokenStore.clear();
    window.dispatchEvent(new CustomEvent("auth:expired"));
    window.dispatchEvent(
      new CustomEvent("app:toast", { detail: { message: "登录已过期，请重新登录", type: "warn" } }),
    );
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.error || body.detail || detail;
    } catch {
      /* 忽略解析失败 */
    }
    // 401/403 不发全局 toast（组件内已有上下文提示）
    if (resp.status !== 401 && resp.status !== 403) {
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: detail, type: "error" } }),
      );
    }
    throw new Error(detail);
  }
  return (await resp.json()) as T;
}

export const api = {
  // ---- 认证 ----
  register(username: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  login(username: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  me(): Promise<UserInfo> {
    return request<UserInfo>("/api/auth/me");
  },
  logout(): Promise<void> {
    return request<void>("/api/auth/logout", { method: "POST" }).catch(() => undefined);
  },

  // ---- 对话 ----
  chat(req: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  // ---- 会话 ----
  listSessions(): Promise<{ sessions: SessionItem[] }> {
    return request<{ sessions: SessionItem[] }>("/api/sessions");
  },
  sessionMessages(sessionId: string): Promise<{ messages: ChatMessage[]; title: string }> {
    return request<{ messages: ChatMessage[]; title: string }>(
      `/api/sessions/${sessionId}/messages`,
    );
  },
  renameSession(sessionId: string, title: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/sessions/${sessionId}/rename`, {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },
  deleteSession(sessionId: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/sessions/${sessionId}`, { method: "DELETE" });
  },
  batchDeleteSessions(sessionIds: string[]): Promise<{ ok: boolean; removed: number }> {
    return request<{ ok: boolean; removed: number }>("/api/sessions/batch-delete", {
      method: "POST",
      body: JSON.stringify({ session_ids: sessionIds }),
    });
  },

  // ---- 知识库 ----
  listDocuments(): Promise<{ documents: DocumentItem[] }> {
    return request<{ documents: DocumentItem[] }>("/api/documents");
  },
  stats(): Promise<StatsResponse> {
    return request<StatsResponse>("/api/stats");
  },
  upload(file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/api/upload", { method: "POST", body: form });
  },
  deleteDocument(docId: string): Promise<{ ok: boolean; removed_chunks?: number }> {
    return request<{ ok: boolean; removed_chunks?: number }>("/api/delete", {
      method: "POST",
      body: JSON.stringify({ doc_id: docId }),
    });
  },

  // ---- 管理后台（admin only） ----
  adminUsers(): Promise<{ users: AdminUserItem[] }> {
    return request<{ users: AdminUserItem[] }>("/api/admin/users");
  },
  adminStats(): Promise<AdminStats> {
    return request<AdminStats>("/api/admin/stats");
  },
  adminStatus(): Promise<SystemStatus> {
    return request<SystemStatus>("/api/admin/status");
  },
  adminSetRole(userId: number, role: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/admin/users/${userId}/set-role?role=${role}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  adminDeleteUser(userId: number): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/admin/users/${userId}/delete`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  adminLogs(limit = 100): Promise<{ logs: AdminLogItem[] }> {
    return request<{ logs: AdminLogItem[] }>(`/api/admin/logs?limit=${limit}`);
  },

  // ---- 版本快照 ----
  backupCreate(description: string): Promise<SnapshotItem> {
    return request<SnapshotItem>(
      `/api/admin/backup/create?description=${encodeURIComponent(description)}`,
      { method: "POST", body: JSON.stringify({}) },
    );
  },
  backupList(): Promise<{ snapshots: SnapshotItem[] }> {
    return request<{ snapshots: SnapshotItem[] }>("/api/admin/backup/list");
  },
  backupRestore(name: string): Promise<{ ok: boolean; count: number }> {
    return request<{ ok: boolean; count: number }>(`/api/admin/backup/${name}/restore`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  backupDelete(name: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/admin/backup/${name}`, { method: "DELETE" });
  },
};
