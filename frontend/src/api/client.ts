// API 客户端：封装与后端的所有交互（带鉴权 token）

import type {
  AdminAccess,
  AdminLogItem,
  AdminStats,
  AdminUserItem,
  DashboardData,
  AuthResponse,
  ChatRequest,
  ChatResponse,
  ChatMessage,
  DocumentItem,
  FeedbackDetail,
  FeedbackListResult,
  FirmInfo,
  CaseSearchResult,
  LawSearchResult,
  LeadCreateBody,
  LeadItem,
  LawyerProfile,
  OpinionResult,
  SceneCatalogResult,
  TemplateDetail,
  TemplateFillResult,
  TemplateListResult,
  CalculatorDetail,
  CalculatorListResult,
  CalculatorRunResult,
  ContractReviewResult,
  ContractReviewStatus,
  UserRecordDetail,
  UserRecordListResult,
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
  sendFeedback(
    messageId: number,
    rating: "useful" | "useless",
    comment = "",
  ): Promise<{ id: number; message_id: number; rating: string }> {
    return request(`/api/chat/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, comment }),
    });
  },
  adminFeedbacks(limit = 100, rating?: string): Promise<FeedbackListResult> {
    const q = new URLSearchParams({ limit: String(limit) });
    if (rating) q.set("rating", rating);
    return request<FeedbackListResult>(`/api/admin/feedbacks?${q}`);
  },
  adminFeedbackDetail(id: number): Promise<FeedbackDetail> {
    return request<FeedbackDetail>(`/api/admin/feedbacks/${id}`);
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
  adminAccess(): Promise<AdminAccess> {
    return request<AdminAccess>("/api/admin/access");
  },
  adminUsers(): Promise<{ users: AdminUserItem[] }> {
    return request<{ users: AdminUserItem[] }>("/api/admin/users");
  },
  adminStats(): Promise<AdminStats> {
    return request<AdminStats>("/api/admin/stats");
  },
  adminDashboard(days = 14): Promise<DashboardData> {
    return request<DashboardData>(`/api/admin/dashboard?days=${days}`);
  },
  adminStatus(): Promise<SystemStatus> {
    return request<SystemStatus>("/api/admin/status");
  },
  adminSetRole(userId: number, role: string, permissions: string[] = []): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/admin/users/${userId}/set-role?role=${role}`, {
      method: "POST",
      body: JSON.stringify({ permissions }),
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

  // ---- 数据备份（运行数据；代码版本用 Git） ----
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

  // ---- 律师 / 免责（M2） ----
  lawyerStatus(): Promise<LawyerProfile> {
    return request<LawyerProfile>("/api/lawyer/status");
  },
  lawyerApplyJson(body: {
    license_no: string;
    region: string;
    specialties: string[];
    profession?: string;
  }): Promise<LawyerProfile> {
    return request<LawyerProfile>("/api/lawyer/apply/json", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  lawyerApply(form: FormData): Promise<LawyerProfile> {
    return request<LawyerProfile>("/api/lawyer/apply", {
      method: "POST",
      body: form,
    });
  },
  adminLawyerPending(): Promise<{ items: LawyerProfile[] }> {
    return request<{ items: LawyerProfile[] }>("/api/admin/lawyer/pending");
  },
  adminLawyerApproved(): Promise<{ items: LawyerProfile[] }> {
    return request<{ items: LawyerProfile[] }>("/api/admin/lawyer/approved");
  },
  adminLawyerReview(userId: number, approve: boolean, reason = ""): Promise<LawyerProfile> {
    return request<LawyerProfile>(`/api/admin/lawyer/${userId}/review`, {
      method: "POST",
      body: JSON.stringify({ approve, reason }),
    });
  },
  adminLawyerBatchReview(
    userIds: number[],
    approve: boolean,
    reason = "",
  ): Promise<{ ok: number; fail: number; failed_ids: number[] }> {
    return request<{ ok: number; fail: number; failed_ids: number[] }>(
      "/api/admin/lawyer/batch-review",
      {
        method: "POST",
        body: JSON.stringify({ user_ids: userIds, approve, reason }),
      },
    );
  },
  adminLawyerRevoke(userId: number, reason = "管理员撤销认证"): Promise<LawyerProfile> {
    return request<LawyerProfile>(`/api/admin/lawyer/${userId}/revoke`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  async adminLawyerFile(userId: number, filename: string): Promise<Blob> {
    const token = tokenStore.get();
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch(
      `${BASE}/api/admin/lawyer/${userId}/files/${encodeURIComponent(filename)}`,
      { headers },
    );
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const body = await resp.json();
        msg = body.error || body.detail || msg;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    return resp.blob();
  },
  disclaimerStatus(): Promise<{ acked: boolean }> {
    return request<{ acked: boolean }>("/api/disclaimer/status");
  },
  disclaimerAck(): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>("/api/disclaimer/ack", {
      method: "POST",
      body: JSON.stringify({}),
    });
  },

  // ---- 案源广场（M3） ----
  listLeads(params?: {
    scope?: "auto" | "mine" | "plaza" | "firm";
    scene?: string;
    region?: string;
  }): Promise<{ items: LeadItem[] }> {
    const q = new URLSearchParams();
    if (params?.scope) q.set("scope", params.scope);
    if (params?.scene) q.set("scene", params.scene);
    if (params?.region) q.set("region", params.region);
    const qs = q.toString();
    return request<{ items: LeadItem[] }>(`/api/leads${qs ? `?${qs}` : ""}`);
  },
  getLead(leadId: number): Promise<LeadItem> {
    return request<LeadItem>(`/api/leads/${leadId}`);
  },
  createLead(body: LeadCreateBody): Promise<LeadItem> {
    return request<LeadItem>("/api/leads", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  claimLead(leadId: number): Promise<LeadItem> {
    return request<LeadItem>(`/api/leads/${leadId}/claim`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  contactLead(
    leadId: number,
    body: { channel: "inbox" | "virtual_number"; message?: string },
  ): Promise<LeadItem> {
    return request<LeadItem>(`/api/leads/${leadId}/contact`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateLeadStatus(leadId: number, status: string): Promise<LeadItem> {
    return request<LeadItem>(`/api/leads/${leadId}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
  },

  // ---- 轻量律所（M3） ----
  createFirm(name: string): Promise<FirmInfo> {
    return request<FirmInfo>("/api/firms", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },
  myFirm(): Promise<FirmInfo> {
    return request<FirmInfo>("/api/firms/me");
  },
  inviteFirmMember(firmId: number, username: string): Promise<{
    firm_id: number;
    user_id: number;
    username: string;
    role: string;
  }> {
    return request(`/api/firms/${firmId}/members`, {
      method: "POST",
      body: JSON.stringify({ username }),
    });
  },

  // ---- 法规 / 类案检索（M4） ----
  searchLaws(q: string, topK = 8): Promise<LawSearchResult> {
    const params = new URLSearchParams({ q, top_k: String(topK) });
    return request<LawSearchResult>(`/api/laws/search?${params}`);
  },
  searchCases(q: string, topK = 6): Promise<CaseSearchResult> {
    const params = new URLSearchParams({ q, top_k: String(topK) });
    return request<CaseSearchResult>(`/api/cases/search?${params}`);
  },

  // ---- 场景目录（M4.3，52 类占位） ----
  listScenes(status?: "active" | "coming_soon"): Promise<SceneCatalogResult> {
    const q = status ? `?status=${status}` : "";
    return request<SceneCatalogResult>(`/api/scenes${q}`);
  },

  // ---- 意见书（M5） ----
  generateOpinion(body: {
    fact_summary: string;
    scene?: string;
    question?: string;
    slot_answers?: Record<string, string>;
    mode?: "lawyer" | "judge" | "prosecutor";
    matter_id?: number | null;
  }): Promise<OpinionResult> {
    return request<OpinionResult>("/api/opinions/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  // ---- 文书模板（M5.2） ----
  listTemplates(audience?: string): Promise<TemplateListResult> {
    const q = audience ? `?audience=${encodeURIComponent(audience)}` : "";
    return request<TemplateListResult>(`/api/templates${q}`);
  },
  getTemplate(id: string): Promise<TemplateDetail> {
    return request<TemplateDetail>(`/api/templates/${id}`);
  },
  fillTemplate(id: string, fields: Record<string, string>): Promise<TemplateFillResult> {
    return request<TemplateFillResult>(`/api/templates/${id}`, {
      method: "POST",
      body: JSON.stringify({ fields }),
    });
  },

  // ---- 法律计算器（M5.3） ----
  listCalculators(audience?: string): Promise<CalculatorListResult> {
    const q = audience ? `?audience=${encodeURIComponent(audience)}` : "";
    return request<CalculatorListResult>(`/api/calculators${q}`);
  },
  getCalculator(id: string): Promise<CalculatorDetail> {
    return request<CalculatorDetail>(`/api/calculators/${id}`);
  },
  runCalculator(
    id: string,
    inputs: Record<string, string | number | boolean>,
  ): Promise<CalculatorRunResult> {
    return request<CalculatorRunResult>(`/api/calculators/${id}`, {
      method: "POST",
      body: JSON.stringify({ inputs }),
    });
  },

  // ---- 合同审查 ----
  contractReviewStatus(): Promise<ContractReviewStatus> {
    return request<ContractReviewStatus>("/api/contracts/review/status");
  },
  contractReview(body: {
    title?: string;
    text: string;
    focus?: string;
    matter_id?: number | null;
  }): Promise<ContractReviewResult> {
    return request<ContractReviewResult>("/api/contracts/review", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  // ---- 案件工作区 ----
  listMatters(roleMode?: string): Promise<import("./types").MatterItem[]> {
    const q = roleMode ? `?role_mode=${encodeURIComponent(roleMode)}` : "";
    return request(`/api/matters${q}`);
  },
  createMatter(body: {
    title: string;
    case_no?: string;
    cause?: string;
    role_mode?: string;
    status?: string;
    meta?: Record<string, unknown>;
  }): Promise<import("./types").MatterItem> {
    return request("/api/matters", { method: "POST", body: JSON.stringify(body) });
  },
  getMatter(id: number): Promise<import("./types").MatterItem> {
    return request(`/api/matters/${id}`);
  },
  updateMatter(
    id: number,
    body: Partial<{
      title: string;
      case_no: string;
      cause: string;
      role_mode: string;
      status: string;
      meta: Record<string, unknown>;
    }>,
  ): Promise<import("./types").MatterItem> {
    return request(`/api/matters/${id}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deleteMatter(id: number): Promise<{ ok: boolean }> {
    return request(`/api/matters/${id}`, { method: "DELETE" });
  },
  listMatterArtifacts(id: number): Promise<import("./types").MatterArtifact[]> {
    return request(`/api/matters/${id}/artifacts`);
  },
  addMatterArtifact(
    id: number,
    body: { kind: string; title?: string; ref_record_id?: number; payload?: Record<string, unknown> },
  ): Promise<import("./types").MatterArtifact> {
    return request(`/api/matters/${id}/artifacts`, { method: "POST", body: JSON.stringify(body) });
  },
  deleteMatterArtifact(matterId: number, artifactId: number): Promise<{ ok: boolean }> {
    return request(`/api/matters/${matterId}/artifacts/${artifactId}`, { method: "DELETE" });
  },
  listMatterDeadlines(id: number): Promise<import("./types").MatterDeadline[]> {
    return request(`/api/matters/${id}/deadlines`);
  },
  addMatterDeadline(
    id: number,
    body: { label: string; due_date?: string | null; calc_key?: string; done?: boolean },
  ): Promise<import("./types").MatterDeadline> {
    return request(`/api/matters/${id}/deadlines`, { method: "POST", body: JSON.stringify(body) });
  },
  updateMatterDeadline(
    matterId: number,
    deadlineId: number,
    body: Partial<{ label: string; due_date: string | null; calc_key: string; done: boolean }>,
  ): Promise<import("./types").MatterDeadline> {
    return request(`/api/matters/${matterId}/deadlines/${deadlineId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  deleteMatterDeadline(matterId: number, deadlineId: number): Promise<{ ok: boolean }> {
    return request(`/api/matters/${matterId}/deadlines/${deadlineId}`, { method: "DELETE" });
  },
  linkMatterRecord(
    matterId: number,
    body: { record_id: number; kind?: string; title?: string },
  ): Promise<import("./types").MatterArtifact> {
    return request(`/api/matters/${matterId}/link-record`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  extractMatterText(
    matterId: number,
    body: { text: string; title?: string },
  ): Promise<import("./types").MatterArtifact> {
    return request(`/api/matters/${matterId}/extract`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  async extractMatterUpload(matterId: number, file: File): Promise<import("./types").MatterArtifact> {
    const headers: Record<string, string> = {};
    const token = tokenStore.get();
    if (token) headers.Authorization = `Bearer ${token}`;
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch(`/api/matters/${matterId}/extract-upload`, {
      method: "POST",
      headers,
      body: fd,
    });
    if (!resp.ok) {
      let detail = `上传抽取失败（HTTP ${resp.status}）`;
      try {
        const body = await resp.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return resp.json();
  },

  listElementCharges(): Promise<{
    items: Array<{
      key: string;
      charge: string;
      category: string;
      article_hint: string;
      element_count: number;
    }>;
    categories: string[];
    total: number;
  }> {
    return request("/api/elements/charges");
  },
  getChargeElements(charge: string): Promise<{
    charge: string;
    article_hint: string;
    category?: string;
    compare?: string[];
    elements: Array<{ id: string; label: string; desc: string; group?: string; evidence?: string }>;
    groups?: Array<{ group: string; items: Array<{ id: string; label: string; desc: string; evidence?: string }> }>;
  }> {
    return request(`/api/elements/${encodeURIComponent(charge)}`);
  },
  checkElements(body: {
    charge: string;
    checked_ids: string[];
    notes?: Record<string, string>;
    matter_id?: number | null;
  }): Promise<import("./types").ElementsCheckResult> {
    return request("/api/elements/check", { method: "POST", body: JSON.stringify(body) });
  },

  listRecords(
    kind: "template" | "calculator" | "contract" | "opinion",
    opts: { page?: number; pageSize?: number; q?: string } = {},
  ): Promise<UserRecordListResult> {
    const q = new URLSearchParams({
      kind,
      page: String(opts.page ?? 1),
      page_size: String(opts.pageSize ?? 10),
    });
    if (opts.q?.trim()) q.set("q", opts.q.trim());
    return request<UserRecordListResult>(`/api/records?${q}`);
  },
  getRecord(id: number): Promise<UserRecordDetail> {
    return request<UserRecordDetail>(`/api/records/${id}`);
  },
  deleteRecord(id: number): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/api/records/${id}`, { method: "DELETE" });
  },
  clearRecords(
    kind: "template" | "calculator" | "contract" | "opinion",
  ): Promise<{ ok: boolean; deleted: number }> {
    return request<{ ok: boolean; deleted: number }>(`/api/records?kind=${kind}`, {
      method: "DELETE",
    });
  },

  async downloadExport(title: string, markdown: string, format: "docx" | "pdf"): Promise<void> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = tokenStore.get();
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch("/api/export", {
      method: "POST",
      headers,
      body: JSON.stringify({ title, markdown, format }),
    });
    if (!resp.ok) {
      let detail = `导出失败（HTTP ${resp.status}）`;
      try {
        const body = await resp.json();
        detail = body.error || body.detail || detail;
      } catch {
        /* 二进制错误体 */
      }
      throw new Error(detail);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safe = (title || "导出文档").replace(/[\\/:*?"<>|]/g, "").slice(0, 80) || "导出文档";
    a.href = url;
    a.download = `${safe}.${format === "pdf" ? "pdf" : "docx"}`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
