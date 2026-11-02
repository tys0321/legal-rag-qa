// 把文书 Markdown 渲成可读预览（标题/加粗/引用），不显示原始 # ** 符号

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s: string): string {
  let t = esc(s);
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/`(.+?)`/g, "<code>$1</code>");
  return t;
}

export function renderMarkdownDoc(md: string): string {
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let para: string[] = [];

  const flush = () => {
    if (!para.length) return;
    out.push(`<p>${inline(para.join(" "))}</p>`);
    para = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const trimmed = line.trim();
    if (!trimmed) {
      flush();
      continue;
    }
    if (/^---+$/.test(trimmed)) {
      flush();
      out.push("<hr/>");
      continue;
    }
    if (trimmed.startsWith("> ")) {
      flush();
      out.push(`<blockquote>${inline(trimmed.slice(2))}</blockquote>`);
      continue;
    }
    const h = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (h) {
      flush();
      const level = h[1].length;
      out.push(`<h${level}>${inline(h[2])}</h${level}>`);
      continue;
    }
    if (/^\*\*.+\*\*$/.test(trimmed) && trimmed.length < 80) {
      flush();
      out.push(`<p class="md-line-strong">${inline(trimmed)}</p>`);
      continue;
    }
    para.push(trimmed);
  }
  flush();
  return out.join("");
}

interface Props {
  markdown: string;
  className?: string;
}

export default function MarkdownDoc({ markdown, className }: Props) {
  return (
    <div
      className={`md-doc ${className || ""}`}
      dangerouslySetInnerHTML={{ __html: renderMarkdownDoc(markdown) }}
    />
  );
}
