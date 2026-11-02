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

/** 槽位选项（ABCD，D 固定为其他情况） */
export interface SlotOption {
  key: string;
  label: string;
}

export interface SlotNeed {
  key: string;
  prompt: string;
  options?: SlotOption[];
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
  need_slots?: SlotNeed[];
  waiting_for_slot?: boolean;
  message_id?: number | null;
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

/** 职业研判草稿：律师意见书 / 法官说理 / 检察审查 */
export type DraftMode = "lawyer" | "judge" | "prosecutor";

export interface OpinionResult {
  scene: string;
  risk_level: string;
  blocked: boolean;
  title: string;
  mode?: DraftMode | string;
  sections: Record<string, string>;
  markdown: string;
  sources: Source[];
  confidence: string;
  watermark: string;
  disclaimer: string;
}

/** 文书模板（M5.2） */
export interface TemplateSummary {
  id: string;
  name: string;
  category: string;
  description: string;
  field_count: number;
}

export interface TemplateField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  placeholder: string;
}

export interface TemplateDetail {
  id: string;
  name: string;
  category: string;
  description: string;
  fields: TemplateField[];
  watermark: string;
  disclaimer: string;
}

export interface TemplateListResult {
  version: number;
  total: number;
  watermark: string;
  items: TemplateSummary[];
}

export interface TemplateFillResult {
  id: string;
  name: string;
  category: string;
  markdown: string;
  watermark: string;
  disclaimer: string;
  missing_required: string[];
}

/** 法律计算器（M5.3） */
export interface CalculatorSummary {
  id: string;
  name: string;
  category: string;
  description: string;
  field_count: number;
}

export interface CalculatorField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  placeholder: string;
  options: string[];
}

export interface CalculatorDetail {
  id: string;
  name: string;
  category: string;
  description: string;
  fields: CalculatorField[];
  notice: string;
}

export interface CalculatorListResult {
  version: number;
  total: number;
  notice: string;
  items: CalculatorSummary[];
}

export interface CalculatorLine {
  label: string;
  value: string;
  amount?: number | null;
}

export interface CalculatorRunResult {
  id: string;
  name: string;
  category: string;
  total: number;
  currency: string;
  lines: CalculatorLine[];
  formula: string;
  notice: string;
  warnings: string[];
  inputs_used: Record<string, unknown>;
}

/** 合同审查占位（M6 / P2） */
export interface ContractReviewStatus {
  available: boolean;
  status: string;
  message: string;
  planned_features: string[];
}

export type UserRecordKind = "template" | "calculator" | "contract" | "opinion";

export interface UserRecordItem {
  id: number;
  kind: string;
  title: string;
  summary: string;
  created_at: string;
}

export interface UserRecordListResult {
  items: UserRecordItem[];
  total: number;
  page: number;
  page_size: number;
  page_count: number;
}

export interface UserRecordDetail extends UserRecordItem {
  payload: Record<string, unknown>;
}

export interface ContractReviewResult {
  available: boolean;
  status: string;
  blocked: boolean;
  message: string;
  title: string;
  focus: string;
  findings: string[];
  markdown: string;
  sources: Array<{
    id: string;
    title: string;
    article?: string;
    text?: string;
  }>;
  watermark: string;
  disclaimer: string;
}

export type Profession = "lawyer" | "judge" | "prosecutor";

export interface LawyerProfile {
  user_id: number;
  username?: string;
  profession?: Profession | string;
  license_no: string;
  region: string;
  specialties: string[];
  license_files: string[];
  status: string;
  reject_reason: string;
  access: string;
  reviewed_at?: string;
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
  /** 后端 messages.id，用于有用/无用反馈 */
  messageId?: number | null;
  feedback?: "useful" | "useless" | null;
  needSlots?: SlotNeed[];
  waitingForSlot?: boolean;
}

export interface FeedbackItem {
  id: number;
  message_id: number;
  user_id: number;
  username: string;
  rating: string;
  comment: string;
  created_at: string;
  message_preview: string;
  question_preview?: string;
  session_id: string;
}

/** 管理端抽检详情：完整问答 */
export interface FeedbackDetail extends FeedbackItem {
  question: string;
  answer: string;
}

export interface FeedbackListResult {
  total: number;
  useful: number;
  useless: number;
  items: FeedbackItem[];
}

/** 管理后台 */
export interface AdminPermItem {
  key: string;
  label: string;
}

export interface AdminAccess {
  is_root: boolean;
  permissions: string[];
  catalog: AdminPermItem[];
}

export interface AdminUserItem {
  id: number;
  username: string;
  role: string;
  created_at: string;
  session_count: number;
  message_count: number;
  permissions?: string[];
  is_root?: boolean;
}

export interface AdminStats {
  user_count: number;
  session_count: number;
  message_count: number;
  doc_count: number;
  chunk_count: number;
}

export interface DayCount {
  date: string;
  count: number;
}

export interface RoleCount {
  role: string;
  count: number;
}

export interface CategoryCount {
  name: string;
  docs: number;
  chunks: number;
}

export interface DashboardSummary {
  user_count: number;
  session_count: number;
  message_count: number;
  doc_count: number;
  chunk_count: number;
  lawyer_pending: number;
  lawyer_approved: number;
  feedback_total: number;
  feedback_useful: number;
  feedback_useless: number;
  useful_rate: number | null;
  avg_messages_per_session: number;
}

export interface DashboardData {
  summary: DashboardSummary;
  roles: RoleCount[];
  daily_messages: DayCount[];
  daily_sessions: DayCount[];
  daily_new_users: DayCount[];
  kb_categories: CategoryCount[];
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

/** 数据备份快照（业务数据，非 Git） */
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
