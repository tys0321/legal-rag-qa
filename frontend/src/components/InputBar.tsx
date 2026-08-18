// 输入栏：多行输入 + 发送，Enter 发送 / Shift+Enter 换行

import { useEffect, useRef, useState } from "react";

interface Props {
  busy: boolean;
  onSend: (text: string) => void;
}

const SUGGESTIONS = [
  "劳动合同法第三十九条是什么？",
  "宪法第三十五条规定的公民权利有哪些？",
  "什么是违约金？",
  "你好",
];

export default function InputBar({ busy, onSend }: Props) {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    taRef.current?.focus();
  }, []);

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
    if (taRef.current) taRef.current.style.height = "auto";
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoGrow = () => {
    const el = taRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 140) + "px";
    }
  };

  return (
    <div className="input-area">
      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" onClick={() => onSend(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>
      <div className="input-row">
        <textarea
          ref={taRef}
          rows={1}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            autoGrow();
          }}
          onKeyDown={onKeyDown}
          placeholder="输入你的法律问题，Enter 发送，Shift+Enter 换行"
        />
        <button className="btn-primary" onClick={submit} disabled={busy || !text.trim()}>
          {busy ? "处理中…" : "发送"}
        </button>
      </div>
      <p className="input-hint">支持追问 · 回答带引用溯源 · 常识问题秒回</p>
    </div>
  );
}
