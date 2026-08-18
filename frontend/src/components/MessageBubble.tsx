// 单条消息气泡：用户/助手，含快慢路径徽标与引用来源

import { useState } from "react";
import type { ChatMessage, RelatedCase, Source } from "../api/types";

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineMarkup(s: string): string {
  // 行内富文本：加粗 → 法条高亮 → 条款高亮 → 行内代码
  let t = escHtml(s);
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/《([^《》]{1,30}?法|[^《》]{1,30}?条例|[^《》]{1,30}?办法|[^《》]{1,30}?规定|[^《》]{1,30}?细则|[^《》]{1,30}?解释)》/g, '<span class="hl-law">《$1》</span>');
  t = t.replace(/(第[一二三四五六七八九十百千万0-9]+[条款款章项])/g, '<span class="hl-article">$1</span>');
  t = t.replace(/`(.+?)`/g, "<code>$1</code>");
  return t;
}

function renderBlock(text: string): string {
  // 块级渲染：编号点 + 缩进子行形成层级结构
  const lines = text.split("\n");
  const out: string[] = [];
  let para: string[] = [];
  // 当前打开的编号点容器：{ title, sub: string[] }
  let openNum: { title: string; sub: string[] } | null = null;

  const closeNum = () => {
    if (openNum) {
      const subHtml = openNum.sub.length
        ? `<div class="md-sub">${inlineMarkup(openNum.sub.join(" "))}</div>`
        : "";
      out.push(
        `<div class="md-num"><span class="md-num-badge">•</span><div class="md-num-content"><span class="md-num-title">${openNum.title}</span>${subHtml}</div></div>`,
      );
      openNum = null;
    }
  };

  const flushPara = () => {
    if (para.length) {
      out.push(`<p>${inlineMarkup(para.join(" "))}</p>`);
      para = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      closeNum();
      flushPara();
      continue;
    }
    // 缩进子行：追加到当前编号点（如"   违反的法律是：……"）
    const indentMatch = line.match(/^(\s{2,}|\t)\s*(.+)$/);
    if (indentMatch && openNum) {
      openNum.sub.push(indentMatch[2]);
      continue;
    }
    // 编号列表：1. **标题** 或 1. 说明
    const numMatch = line.match(/^(\s*)(\d+)[.、．]\s+(.*)$/);
    if (numMatch) {
      closeNum();
      flushPara();
      openNum = { title: inlineMarkup(numMatch[3]), sub: [] };
      continue;
    }
    // 项目符号：- 或 •
    const dashMatch = line.match(/^(\s*)[-•·]\s+(.*)$/);
    if (dashMatch) {
      closeNum();
      flushPara();
      out.push(`<div class="md-num"><span class="md-num-badge">•</span><div class="md-num-content">${inlineMarkup(dashMatch[2])}</div></div>`);
      continue;
    }
    // 加粗小节标题：**标题**
    const boldMatch = line.match(/^\*{1,2}(.+?)\*{1,2}\s*$/);
    if (boldMatch && line.trim().length <= 40) {
      closeNum();
      flushPara();
      out.push(`<div class="md-section">${inlineMarkup(boldMatch[1])}</div>`);
      continue;
    }
    closeNum();
    para.push(line.trim());
  }
  closeNum();
  flushPara();
  return out.join("");
}

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (message.role === "user") {
    return (
      <div className="msg user">
        <div className="avatar">👤</div>
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  const sources = message.sources ?? [];
  return (
    <div className="msg ai">
      <div className="avatar">⚖️</div>
      <div className="bubble">
        {message.error ? (
          <span className="err-text">{message.content}</span>
        ) : (
          <>
            <div dangerouslySetInnerHTML={{ __html: renderBlock(message.content) }} />
            {message.mode && (
              <div className="meta">
                <span className={`badge ${message.mode}`}>
                  {message.mode === "fast" ? "⚡ 常识回答" : "📚 知识库回答"}
                </span>
                {sources.length > 0 && (
                  <button className="src-btn" onClick={() => setExpanded((v) => !v)}>
                    {expanded ? "收起引用来源" : `查看 ${sources.length} 个引用来源`}
                  </button>
                )}
              </div>
            )}
            {expanded && sources.length > 0 && (
              <SourceList sources={sources} />
            )}
            {message.relatedCases && message.relatedCases.length > 0 && (
              <RelatedCases cases={message.relatedCases} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function statusBadge(status?: string) {
  if (!status || status === "现行有效") return null;
  const cls =
    status === "已废止" ? "st-repealed" : status === "已修订" ? "st-revised" : "st-partial";
  return <span className={`src-tag ${cls}`}>{status}</span>;
}

function SourceList({ sources }: { sources: Source[] }) {
  return (
    <div className="inline-sources">
      <div className="src-title">引用来源：</div>
      {sources.map((s, i) => (
        <details className="src-item" key={s.id + i}>
          <summary>
            <span className="src-num">{i + 1}</span>
            <span className="src-loc">
              {s.title}
              {s.article ? `（${s.article}）` : ""}
            </span>
            {s.match === "article" && <span className="src-tag">条款匹配</span>}
            {statusBadge(s.effective_status)}
          </summary>
          <div className="src-body">
            {s.effective_detail && (
              <p className="src-eff">
                {s.effective_detail}
              </p>
            )}
            <p>{s.text}</p>
            <p className="src-meta">
              相关度 {s.score} · {s.category}
              {s.page ? ` · 第${s.page}页` : ""}
            </p>
          </div>
        </details>
      ))}
    </div>
  );
}

function RelatedCases({ cases }: { cases: RelatedCase[] }) {
  return (
    <div className="related-cases">
      <div className="src-title">📎 相似案例推荐：</div>
      {cases.map((c) => (
        <details className="src-item" key={c.id}>
          <summary>
            <span className="src-num">案</span>
            <span className="src-loc">{c.title}</span>
            <span className="src-tag">{c.category}</span>
          </summary>
          <div className="src-body">
            <p>{c.text.slice(0, 300)}</p>
            <p className="src-meta">相关度 {c.score}</p>
          </div>
        </details>
      ))}
    </div>
  );
}
