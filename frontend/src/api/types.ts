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
  mode: "fast" | "slow" | "slot" | "risk_block";
  sources: Source[];
  disclaimer: string;
  routed_reason: string;
  related_cases: RelatedCase[];
  confidence?: "high" | "medium" | "low";
  critic_issues?: string[];
  risk_level?: "L1" | "L2" | "L3";
  risk_banner?: string;
  force_lawyer_cta?: boolean;
  scene?: string;
  need_slots?: { key: string; prompt: string }[];
  waiting_for_slot?: boolean;
}

/** 对话请求 */
export interface ChatRequest {
  message: string;
  session_id: string | null;
  scene?: string | null;
  skip_slots?: boolean;
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
  lawyer_access?: string;
  lawyer_status?: string;
  disclaimer_acked?: boolean;
  firm_id?: number | null;
  firm_name?: string;
  firm_role?: string;
}

/** 案源（M3） */
export interface LeadEvent {
  id: number;
  lead_id: number;
  actor_id?: number | null;
  event_type: string;
  detail: string;
  created_at: string;
}

export interface LeadItem {
  id: number;
  user_id: number;
  scene: string;
  region: string;
  title: string;
  summary: string;
  status: string;
  claimed_by?: number | null;
  firm_visible: boolean;
  contact_masked: string;
  allow_push: boolean;
  match_score: number;
  virtual_number: string;
  created_at: string;
  updated_at: string;
  events?: LeadEvent[];
}

export interface LeadCreateBody {
  title: string;
  summary: string;
  scene: string;
  region: string;
  contact: string;
  allow_push?: boolean;
  firm_visible?: boolean;
  publish?: boolean;
}

export interface FirmMember {
  firm_id: number;
  user_id: number;
  username: string;
  role: string;
  joined_at: string;
}

export interface FirmInfo {
  id: number;
  name: string;
  owner_user_id: number;
  created_at: string;
  members: FirmMember[];
}

/** 法规检索命中（M4） */
export interface LawHit {
  id: string;
  doc_id: string;
  title: string;
  category: string;
  article: string;
  page: number;
  text: string;
  score: number;
  match?: string | null;
  rrf_score?: number | null;
  effective_status: string;
  effective_detail: string;
  bian?: string;
  chapter?: string;
  section?: string;
}

export interface LawSearchResult {
  query: string;
  backend: string;
  total: number;
  items: LawHit[];
}

/** 类案卡（M4） */
export interface CaseHit {
  id: string;
  doc_id: string;
  title: string;
  category: string;
  article: string;
  page: number;
  text: string;
  score: number;
  kind: string;
}

export interface CaseSearchResult {
  query: string;
  backend: string;
  total: number;
  notice: string;
  items: CaseHit[];
}

/** 52 场景目录（M4） */
export interface SceneCatalogItem {
  id: string;
  name: string;
  group: string;
  status: "active" | "coming_soon" | string;
  alias: string;
}

export interface SceneCatalogResult {
  version: number;
  total: number;
  active_count: number;
  coming_soon_count: number;
  mvp_ids: string[];
  groups: Record<string, number>;
  items: SceneCatalogItem[];
}

/** 法律意见书（M5） */
export interface OpinionResult {
  scene: string;
  risk_level: string;
  blocked: boolean;
  title: string;
  sections: {
    case_summary?: string;
    legal_analysis?: string;
    action_advice?: string;
    disclaimer?: string;
  };
  markdown: string;
  sources: Source[];
  confidence: string;
  watermark: string;
  disclaimer: string;
}

export interface LawyerProfile {
  user_id: number;
  username?: string;
  license_no: string;
  region: string;
  specialties: string[];
  license_files: string[];
  status: string;
  reject_reason: string;
  access: string;
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
  mode?: "fast" | "slow" | "slot" | "risk_block";
  sources?: Source[];
  relatedCases?: RelatedCase[];
  confidence?: "high" | "medium" | "low";
  riskLevel?: string;
  riskBanner?: string;
  forceLawyerCta?: boolean;
  scene?: string;
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
