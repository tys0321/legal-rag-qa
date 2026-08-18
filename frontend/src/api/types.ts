// 与后端 API 契约对齐的类型定义

/** 引用来源（检索命中） */
export interface Source {
  id: string;
  doc_id: string;
  title: string;
  category: string;
  article: string;
  page: number;
  text: string;
  score: number;
  match?: "article" | "vector";
  effective_status?: string;
  effective_detail?: string;
}

/** 相似案例推荐 */
export interface RelatedCase {
  id: string;
  doc_id: string;
  title: string;
  category: string;
  text: string;
  score: number;
}

/** 问答响应 */
export interface ChatResponse {
  session_id: string;
  answer: string;
  mode: "fast" | "slow";
  sources: Source[];
  disclaimer: string;
  routed_reason: string;
  related_cases: RelatedCase[];
}

/** 对话请求 */
export interface ChatRequest {
  message: string;
  session_id: string | null;
}

/** 认证 */
export interface AuthResponse {
  token: string;
  username: string;
  user_id: number;
  role?: string;
}

export interface UserInfo {
  id: number;
  username: string;
  created_at: string;
  role?: string;
}

/** 会话条目 */
export interface SessionItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  msg_count: number;
}

export interface SessionListResponse {
  sessions: SessionItem[];
  messages?: ChatMessage[];
  title?: string;
}

/** 文档条目 */
export interface DocumentItem {
  doc_id: string;
  title: string;
  category: string;
  chunks: number;
  effective_status?: string;
  effective_detail?: string;
}

/** 知识库统计 */
export interface StatsResponse {
  chunk_count: number;
  doc_count: number;
  docs: Record<string, { title: string; category: string; chunks: number }>;
}

/** 上传响应 */
export interface UploadResponse {
  ok: boolean;
  doc_id?: string;
  title?: string;
  category?: string;
  chunks_added?: number;
  status?: string;
  ocr_pages?: number;
  pending?: boolean;
  error?: string | null;
}

/** 前端消息模型 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: "fast" | "slow";
  sources?: Source[];
  relatedCases?: RelatedCase[];
  error?: boolean;
}

/** 管理后台 */
export interface AdminUserItem {
  id: number;
  username: string;
  role: string;
  created_at: string;
  session_count: number;
  message_count: number;
}

export interface AdminStats {
  user_count: number;
  session_count: number;
  message_count: number;
  doc_count: number;
  chunk_count: number;
}

export interface SystemStatus {
  chat_model: string;
  embedding_model: string;
  embedding_dim: number;
  ocr_enabled: boolean;
  effective_status_enabled: boolean;
  vector_store: string;
  kb_source: string;
}

/** 版本快照 */
export interface SnapshotItem {
  name: string;
  description: string;
  created_at: string;
  size_mb: number;
}

/** 操作日志 */
export interface AdminLogItem {
  id: number;
  actor_id: number | null;
  actor_name: string;
  action: string;
  detail: string;
  created_at: string;
}
