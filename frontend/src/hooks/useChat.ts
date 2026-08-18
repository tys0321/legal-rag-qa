// 对话状态管理 hook：发送消息、切换历史会话、新建会话

import { useCallback, useState } from "react";
import { api } from "../api/client";
import type { ChatMessage } from "../api/types";

export interface ChatController {
  messages: ChatMessage[];
  busy: boolean;
  activeSessionId: string | null;
  send: (text: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  newSession: () => void;
}

let seq = 0;
function nextId(): string {
  seq += 1;
  return `m${Date.now()}-${seq}`;
}

export function useChat(): ChatController {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || busy) return;

      const userMsg: ChatMessage = { id: nextId(), role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setBusy(true);

      try {
        const resp = await api.chat({ message: trimmed, session_id: activeSessionId });
        setActiveSessionId(resp.session_id);

        const aiMsg: ChatMessage = {
          id: nextId(),
          role: "assistant",
          content: resp.answer,
          mode: resp.mode,
          sources: resp.sources ?? [],
          relatedCases: resp.related_cases ?? [],
        };
        setMessages((prev) => [...prev, aiMsg]);
        // 通知侧边栏刷新会话列表
        window.dispatchEvent(new CustomEvent("sessions:changed"));
      } catch (err) {
        const aiMsg: ChatMessage = {
          id: nextId(),
          role: "assistant",
          content: `⚠️ ${err instanceof Error ? err.message : "请求失败"}`,
          error: true,
        };
        setMessages((prev) => [...prev, aiMsg]);
      } finally {
        setBusy(false);
      }
    },
    [busy, activeSessionId],
  );

  const loadSession = useCallback(async (sessionId: string) => {
    setBusy(true);
    try {
      const data = await api.sessionMessages(sessionId);
      const loaded = (data.messages ?? []).map((m) => ({
        ...m,
        id: m.id ?? nextId(),
      }));
      setMessages(loaded);
      setActiveSessionId(sessionId);
    } catch {
      /* 加载失败保持现状 */
    } finally {
      setBusy(false);
    }
  }, []);

  const newSession = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
  }, []);

  return { messages, busy, activeSessionId, send, loadSession, newSession };
}
