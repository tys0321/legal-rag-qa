// 单条消息气泡：用户/助手，含快慢路径徽标、引用来源与法条点击跳转

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChatMessage, RelatedCase, Source } from "../api/types";

interface BubbleProps {
  message: ChatMessage;
  onPublishLead?: (scene?: string) => void;
  onFeedback?: (messageId: number, rating: "useful" | "useless") => void;
}

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineMarkup(s: string): string {
  let t = escHtml(s);
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  const held: string[] = [];
  const hold = (html: string) => {
    held.push(html);
    return `\u0000H${held.length - 1}\u0000`;
  };
  // 《法名》第X条 成组可点（高亮保留）
  t = t.replace(
    /《([^《》]{1,40}?)》(第[一二三四五六七八九十百千万0-9]+条)/g,
    (_m, law: string, art: string) =>
      hold(
        `<button type="button" class="hl-law cite-jump" data-cite-law="${law}" data-cite-article="${art}">《${law}》${art}</button>`,
      ),
  );
  t = t.replace(
    /《([^《》]{1,30}?法|[^《》]{1,30}?条例|[^《》]{1,30}?办法|[^《》]{1,30}?规定|[^《》]{1,30}?细则|[^《》]{1,30}?解释)》/g,
    (_m, law: string) =>
      hold(`<button type="button" class="hl-law cite-jump" data-cite-law="${law}">《${law}》</button>`),
  );
  t = t.replace(
    /(第[一二三四五六七八九十百千万0-9]+[条款款章项])/g,
    (_m, art: string) =>
      hold(`<button type="button" class="hl-article cite-jump" data-cite-article="${art}">${art}</button>`),
  );
  // [1][2] 引用编号 → 跳到对应来源
  t = t.replace(/\[(\d+)\]/g, (_m, n: string) =>
    hold(`<button type="button" class="hl-cite cite-jump" data-cite-idx="${n}">[${n}]</button>`),
  );
  t = t.replace(/`(.+?)`/g, "<code>$1</code>");
  t = t.replace(/\u0000H(\d+)\u0000/g, (_m, i: string) => held[Number(i)] || "");
  return t;
}

function renderBlock(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  let para: string[] = [];
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
    const indentMatch = line.match(/^(\s{2,}|\t)\s*(.+)$/);
    if (indentMatch && openNum) {
      openNum.sub.push(indentMatch[2]);
      continue;
    }
    const numMatch = line.match(/^(\s*)(\d+)[.、．]\s+(.*)$/);
    if (numMatch) {
      closeNum();
      flushPara();
      openNum = { title: inlineMarkup(numMatch[3]), sub: [] };
      continue;
    }
    const dashMatch = line.match(/^(\s*)[-•·]\s+(.*)$/);
    if (dashMatch) {
      closeNum();
      flushPara();
      out.push(
        `<div class="md-num"><span class="md-num-badge">•</span><div class="md-num-content">${inlineMarkup(dashMatch[2])}</div></div>`,
      );
      continue;
    }
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

function matchSourceIndex(
  sources: Source[],
  law?: string | null,
  article?: string | null,
): number {
  if (!sources.length) return -1;
  const norm = (s: string) => s.replace(/\s+/g, "");
  if (article) {
    const a = norm(article);
    const byArt = sources.findIndex(
      (s) => s.article && (norm(s.article) === a || norm(s.article).includes(a) || a.includes(norm(s.article))),
    );
    if (byArt >= 0) return byArt;
  }
  if (law) {
    const l = norm(law);
    const byTitle = sources.findIndex((s) => {
      const t = norm(s.title || "");
      return t.includes(l) || l.includes(t) || t.includes(`《${l}》`);
    });
    if (byTitle >= 0) return byTitle;
    const byText = sources.findIndex((s) => norm(s.text || "").includes(l));
    if (byText >= 0) return byText;
  }
  return 0;
}

export default function MessageBubble({ message, onPublishLead, onFeedback }: BubbleProps) {
  const [expanded, setExpanded] = useState(false);
  const [focusIdx, setFocusIdx] = useState<number | null>(null);
  const [fbBusy, setFbBusy] = useState(false);
  const [localFb, setLocalFb] = useState<"useful" | "useless" | null>(message.feedback ?? null);
  const [lookup, setLookup] = useState<{ title: string; article: string; text: string } | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const sourcesRef = useRef<HTMLDivElement>(null);

  const sources = message.sources ?? [];

  useEffect(() => {
    if (!expanded || focusIdx == null) return;
    const el = sourcesRef.current?.querySelector(`[data-src-idx="${focusIdx}"]`) as HTMLDetailsElement | null;
    if (el) {
      el.open = true;
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [expanded, focusIdx]);

  const openSourceIdx = (idx: number) => {
    setFocusIdx(idx);
    setExpanded(true);
    setLookup(null);
  };

  const jumpToCite = async (law?: string | null, article?: string | null, citeIdx?: string | null) => {
    if (citeIdx) {
      const n = Number(citeIdx);
      if (Number.isFinite(n) && n >= 1 && n <= sources.length) {
        openSourceIdx(n - 1);
        return;
      }
    }
    if (sources.length) {
      const idx = matchSourceIndex(sources, law, article);
      if (idx >= 0) {
        openSourceIdx(idx);
        return;
      }
    }
    // 本次回答未挂来源时，按法名/条号去知识库检索并弹出原文
    const q = [law, article].filter(Boolean).join(" ").trim();
    if (!q) {
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: "未找到可跳转的法条原文", type: "warn" },
        }),
      );
      return;
    }
    setLookupBusy(true);
    try {
      const res = await api.searchLaws(q, 5);
      const hit = res.items?.[0];
      if (!hit) {
        window.dispatchEvent(
          new CustomEvent("app:toast", {
            detail: { message: "知识库中未检索到该法条", type: "warn" },
          }),
        );
        return;
      }
      setLookup({
        title: hit.title || law || "法规",
        article: hit.article || article || "",
        text: hit.text || "",
      });
    } catch (err) {
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: err instanceof Error ? err.message : "检索失败", type: "error" },
        }),
      );
    } finally {
      setLookupBusy(false);
    }
  };

  const onBodyClick = (e: React.MouseEvent) => {
    const t = (e.target as HTMLElement).closest(".cite-jump") as HTMLElement | null;
    if (!t) return;
    e.preventDefault();
    void jumpToCite(
      t.getAttribute("data-cite-law"),
      t.getAttribute("data-cite-article"),
      t.getAttribute("data-cite-idx"),
    );
  };

  const submitFeedback = async (rating: "useful" | "useless") => {
    if (!message.messageId || fbBusy) return;
    setFbBusy(true);
    try {
      await api.sendFeedback(message.messageId, rating);
      setLocalFb(rating);
      onFeedback?.(message.messageId, rating);
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: rating === "useful" ? "已标记有用" : "已标记无用", type: "success" },
        }),
      );
    } catch (err) {
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: err instanceof Error ? err.message : "反馈失败", type: "error" },
        }),
      );
    } finally {
      setFbBusy(false);
    }
  };

  if (message.role === "user") {
    return (
      <div className="msg user">
        <div className="avatar">👤</div>
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  const modeLabel =
    message.mode === "fast"
      ? "⚡ 常识回答"
      : message.mode === "slot"
        ? "🧩 补充案情"
        : message.mode === "risk_block"
          ? "⛔ 风险拦截"
          : "📚 知识库回答";

  return (
    <div className="msg ai">
      <div className="avatar">⚖️</div>
      <div className="bubble">
        {message.error ? (
          <span className="err-text">{message.content}</span>
        ) : (
          <>
            <div
              ref={bodyRef}
              onClick={onBodyClick}
              dangerouslySetInnerHTML={{ __html: renderBlock(message.content) }}
            />
            <p className="answer-disclaimer">
              ⚠️ 以上内容由 AI 基于知识库生成，仅供参考，不构成正式法律意见。
            </p>
            {message.mode && (
              <div className="meta">
                <span className={`badge ${message.mode}`}>{modeLabel}</span>
                {message.confidence && (
                  <span className={`badge conf-${message.confidence}`}>
                    {message.confidence === "high"
                      ? "置信度：高"
                      : message.confidence === "low"
                        ? "置信度：低"
                        : "置信度：中"}
                  </span>
                )}
                {message.scene && <span className="badge scene">{message.scene}</span>}
                {sources.length > 0 && (
                  <button className="src-btn" type="button" onClick={() => setExpanded((v) => !v)}>
                    {expanded ? "收起引用来源" : `查看 ${sources.length} 个引用来源`}
                  </button>
                )}
              </div>
            )}
            {message.forceLawyerCta && (
              <div className="cta-row">
                <button
                  type="button"
                  className="cta-lawyer"
                  onClick={() => onPublishLead?.(message.scene)}
                >
                  发布案源需求
                </button>
              </div>
            )}
            {lookupBusy && <p className="muted cite-lookup-hint">正在定位法条原文…</p>}
            {lookup && (
              <div className="cite-lookup-panel">
                <div className="cite-lookup-head">
                  <strong>
                    《{lookup.title}》
                    {lookup.article ? ` ${lookup.article}` : ""}
                  </strong>
                  <button type="button" className="btn-ghost btn-sm" onClick={() => setLookup(null)}>
                    关闭
                  </button>
                </div>
                <p className="cite-lookup-body">{lookup.text}</p>
              </div>
            )}
            {expanded && sources.length > 0 && (
              <div ref={sourcesRef}>
                <SourceList sources={sources} focusIdx={focusIdx} />
              </div>
            )}
            {message.relatedCases && message.relatedCases.length > 0 && (
              <RelatedCases cases={message.relatedCases} />
            )}
            {message.messageId && !message.error && (
              <div className="fb-row">
                <span className="fb-label">这条回答</span>
                <button
                  type="button"
                  className={`fb-btn ${localFb === "useful" ? "active" : ""}`}
                  disabled={fbBusy}
                  onClick={() => void submitFeedback("useful")}
                >
                  有用
                </button>
                <button
                  type="button"
                  className={`fb-btn ${localFb === "useless" ? "active" : ""}`}
                  disabled={fbBusy}
                  onClick={() => void submitFeedback("useless")}
                >
                  无用
                </button>
              </div>
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

function SourceList({ sources, focusIdx }: { sources: Source[]; focusIdx: number | null }) {
  return (
    <div className="inline-sources">
      <div className="src-title">引用来源：</div>
      {sources.map((s, i) => (
        <details
          className={`src-item ${focusIdx === i ? "src-focus" : ""}`}
          key={s.id + i}
          data-src-idx={i}
          open={focusIdx === i ? true : undefined}
        >
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
            {s.effective_detail && <p className="src-eff">{s.effective_detail}</p>}
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
