// 统一引用卡片：效力徽章 + 正文可展开

import { useState } from "react";

export type SourceLike = {
  id?: string;
  title?: string;
  article?: string;
  text?: string;
  category?: string;
  page?: number;
  score?: number;
  match?: string | null;
  effective_status?: string;
  effective_detail?: string;
};

function statusClass(status?: string) {
  if (!status || status === "现行有效") return "st-ok";
  if (status === "已废止") return "st-repealed";
  if (status === "已修订") return "st-revised";
  return "st-partial";
}

interface Props {
  sources: SourceLike[];
  title?: string;
}

export default function SourceCard({ sources, title = "引用" }: Props) {
  const [openId, setOpenId] = useState<string | null>(sources[0]?.id ?? null);
  if (!sources.length) return null;

  return (
    <section className="opinion-section source-card-list">
      <h3>{title}</h3>
      <ul className="source-cards">
        {sources.map((s, i) => {
          const key = s.id || String(i);
          const open = openId === key;
          const status = s.effective_status || "";
          const warn = status && status !== "现行有效";
          return (
            <li key={key} className={`source-card ${warn ? "source-card-warn" : ""}`}>
              <button
                type="button"
                className="source-card-head"
                onClick={() => setOpenId(open ? null : key)}
              >
                <span className="src-num">{i + 1}</span>
                <span className="source-card-title">
                  {s.title || "未命名"}
                  {s.article ? ` · ${s.article}` : ""}
                </span>
                {status && (
                  <span className={`src-tag ${statusClass(status)}`}>{status}</span>
                )}
                {s.match === "article" && <span className="src-tag">条款匹配</span>}
              </button>
              {open && (
                <div className="source-card-body">
                  {s.effective_detail && <p className="src-eff">{s.effective_detail}</p>}
                  <p className="law-excerpt">{s.text || "（无摘录正文）"}</p>
                  <p className="muted">
                    {s.category || ""}
                    {typeof s.score === "number" ? ` · 相关度 ${s.score.toFixed?.(3) ?? s.score}` : ""}
                    {s.page ? ` · 第${s.page}页` : ""}
                  </p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
