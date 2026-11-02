// 运营数据看板：KPI + 趋势柱图 + 角色/知识库分布

import type { DashboardData, DayCount } from "../api/types";

interface Props {
  data: DashboardData;
  days: number;
  onDaysChange: (d: number) => void;
  onGoto: (nav: "lawyers" | "kb" | "users" | "feedbacks" | "ops") => void;
}

const ROLE_LABEL: Record<string, string> = {
  user: "普通用户",
  lawyer: "律师",
  judge: "法官",
  prosecutor: "检察官",
  admin: "管理员",
};

function BarChart({
  title,
  series,
  color,
}: {
  title: string;
  series: DayCount[];
  color: string;
}) {
  const max = Math.max(1, ...series.map((s) => s.count));
  const total = series.reduce((a, s) => a + s.count, 0);
  return (
    <section className="db-chart-card">
      <div className="db-chart-head">
        <h3>{title}</h3>
        <span>合计 {total}</span>
      </div>
      <div className="db-bars" role="img" aria-label={title}>
        {series.map((s) => {
          const h = Math.max(4, Math.round((s.count / max) * 100));
          const label = s.date.slice(5);
          return (
            <div className="db-bar-col" key={s.date} title={`${s.date}: ${s.count}`}>
              <div className="db-bar-track">
                <div className="db-bar" style={{ height: `${h}%`, background: color }} />
              </div>
              <span className="db-bar-val">{s.count || ""}</span>
              <span className="db-bar-label">{label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function AdminDashboard({ data, days, onDaysChange, onGoto }: Props) {
  const s = data.summary;
  const roleTotal = data.roles.reduce((a, r) => a + r.count, 0) || 1;
  const catMax = Math.max(1, ...data.kb_categories.map((c) => c.chunks));

  return (
    <div className="db-board">
      <div className="db-toolbar">
        <div className="db-range">
          <span>统计区间</span>
          {([7, 14, 30] as const).map((d) => (
            <button
              key={d}
              type="button"
              className={days === d ? "active" : ""}
              onClick={() => onDaysChange(d)}
            >
              近 {d} 日
            </button>
          ))}
        </div>
        {s.lawyer_pending > 0 && (
          <button type="button" className="ac-btn-solid" onClick={() => onGoto("lawyers")}>
            {s.lawyer_pending} 份认证待审 →
          </button>
        )}
      </div>

      <div className="db-kpi-grid">
        <button type="button" className="db-kpi" onClick={() => onGoto("users")}>
          <div className="db-kpi-label">注册用户</div>
          <div className="db-kpi-num">{s.user_count}</div>
          <div className="db-kpi-sub">点击查看账号</div>
        </button>
        <div className="db-kpi">
          <div className="db-kpi-label">咨询会话</div>
          <div className="db-kpi-num">{s.session_count}</div>
          <div className="db-kpi-sub">均 {s.avg_messages_per_session} 条/会话</div>
        </div>
        <div className="db-kpi">
          <div className="db-kpi-label">消息总量</div>
          <div className="db-kpi-num">{s.message_count}</div>
          <div className="db-kpi-sub">近 {days} 日见趋势图</div>
        </div>
        <button type="button" className="db-kpi" onClick={() => onGoto("kb")}>
          <div className="db-kpi-label">知识库</div>
          <div className="db-kpi-num">{s.doc_count}</div>
          <div className="db-kpi-sub">{s.chunk_count} 检索片段</div>
        </button>
        <button type="button" className="db-kpi accent" onClick={() => onGoto("lawyers")}>
          <div className="db-kpi-label">律师认证</div>
          <div className="db-kpi-num">{s.lawyer_pending}</div>
          <div className="db-kpi-sub">待审 · 已认证 {s.lawyer_approved}</div>
        </button>
        <button type="button" className="db-kpi" onClick={() => onGoto("feedbacks")}>
          <div className="db-kpi-label">回答有用率</div>
          <div className="db-kpi-num">
            {s.useful_rate == null ? "—" : `${s.useful_rate}%`}
          </div>
          <div className="db-kpi-sub">
            有用 {s.feedback_useful} / 无用 {s.feedback_useless}
          </div>
        </button>
      </div>

      <div className="db-charts">
        <BarChart title="每日消息量" series={data.daily_messages} color="#1a365d" />
        <BarChart title="每日新会话" series={data.daily_sessions} color="#2a5ee8" />
        <BarChart title="每日新注册" series={data.daily_new_users} color="#c9a227" />
      </div>

      <div className="db-split">
        <section className="db-panel">
          <div className="db-panel-head">
            <h3>用户角色构成</h3>
            <button type="button" className="ac-btn-ghost" onClick={() => onGoto("users")}>
              用户管理
            </button>
          </div>
          {data.roles.length === 0 ? (
            <p className="ac-empty">暂无用户数据</p>
          ) : (
            <ul className="db-role-list">
              {data.roles.map((r) => {
                const pct = Math.round((r.count / roleTotal) * 100);
                return (
                  <li key={r.role}>
                    <div className="db-role-meta">
                      <strong>{ROLE_LABEL[r.role] || r.role}</strong>
                      <span>
                        {r.count}（{pct}%）
                      </span>
                    </div>
                    <div className="db-role-bar">
                      <i style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="db-panel">
          <div className="db-panel-head">
            <h3>知识库分类</h3>
            <button type="button" className="ac-btn-ghost" onClick={() => onGoto("kb")}>
              知识库
            </button>
          </div>
          {data.kb_categories.length === 0 ? (
            <p className="ac-empty">暂无入库文档</p>
          ) : (
            <ul className="db-cat-list">
              {data.kb_categories.slice(0, 8).map((c) => (
                <li key={c.name}>
                  <div className="db-cat-meta">
                    <strong>{c.name}</strong>
                    <span>
                      {c.docs} 文档 · {c.chunks} 块
                    </span>
                  </div>
                  <div className="db-role-bar">
                    <i
                      style={{
                        width: `${Math.round((c.chunks / catMax) * 100)}%`,
                        background: "linear-gradient(90deg,#2a5ee8,#1a365d)",
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
