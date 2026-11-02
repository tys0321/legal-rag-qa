// 从业者问答：主区只负责对话；历史与入口在左侧栏

import { useEffect, useRef } from "react";
import type { ChatController } from "../hooks/useChat";
import MessageBubble from "./MessageBubble";
import SlotChoiceBar from "./SlotChoiceBar";

interface Props {
  hint: string;
  chat: ChatController;
}

export default function ProAskPanel({ hint, chat }: Props) {
  const { messages, busy, activeSessionId, send, slotPrompt, clearSlot } = chat;
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeSessionId]);

  const submit = () => {
    const el = inputRef.current;
    if (!el) return;
    const t = el.value.trim();
    if (!t || busy) return;
    el.value = "";
    el.style.height = "auto";
    void send(t);
  };

  return (
    <div className="pro-ask-shell pro-ask-shell-flat">
      <div className="pro-ask-main">
        <header className="pro-ask-main-head">
          <div>
            <h2>问答检索</h2>
            <p className="muted">{hint}</p>
          </div>
        </header>

        <div className="pro-ask-thread">
          {messages.length === 0 && (
            <div className="pro-ask-empty">
              <p>直接输入争点、要件或程序问题；回答附法规/类案引用。</p>
              <p className="muted">左侧可新建或切换会话。已认证账号不会再弹出基础案情选择题。</p>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {busy && (
            <div className="msg ai">
              <div className="avatar">⚖️</div>
              <div className="bubble typing">检索中…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="pro-ask-composer">
          {slotPrompt ? (
            <SlotChoiceBar
              busy={busy}
              prompt={slotPrompt.prompt}
              options={slotPrompt.options}
              onChoose={(text) => void send(text)}
              onCancel={clearSlot}
            />
          ) : (
            <div className="pro-ask-input-row">
              <textarea
                ref={inputRef}
                rows={2}
                placeholder="输入问题，Enter 发送，Shift+Enter 换行"
                disabled={busy}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
                }}
              />
              <button type="button" className="btn-primary" disabled={busy} onClick={submit}>
                {busy ? "…" : "发送"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
