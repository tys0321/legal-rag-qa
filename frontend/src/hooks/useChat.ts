// 对话状态管理 hook：发送消息、切换历史会话、新建会话、槽位 ABCD

import { useCallback, useState } from "react";
import { api } from "../api/client";
import type { ChatMessage, SlotOption } from "../api/types";

export interface SlotPromptState {
  key: string;
  prompt: string;
  options: SlotOption[];
}

export interface ChatController {
  messages: ChatMessage[];
  busy: boolean;
  activeSessionId: string | null;
  slotPrompt: SlotPromptState | null;
  send: (text: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  newSession: () => void;
  clearSlot: () => void;
}

let seq = 0;
function nextId(): string {
  seq += 1;
  return `m${Date.now()}-${seq}`;
}

function pickSlotPrompt(
  needSlots?: { key: string; prompt: string; options?: SlotOption[] }[],
  waiting?: boolean,
): SlotPromptState | null {
  if (!waiting || !needSlots?.length) return null;
  const first = needSlots[0];
  const options =
    first.options && first.options.length > 0
      ? first.options
      : [
          { key: "A", label: "是" },
          { key: "B", label: "否" },
          { key: "C", label: "不确定" },
          { key: "D", label: "其他情况" },
        ];
  return { key: first.key, prompt: first.prompt, options };
}

export function useChat(): ChatController {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [slotPrompt, setSlotPrompt] = useState<SlotPromptState | null>(null);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || busy) return;

      const userMsg: ChatMessage = { id: nextId(), role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setBusy(true);
      setSlotPrompt(null);

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
          confidence: resp.confidence,
          riskLevel: resp.risk_level,
          riskBanner: resp.risk_banner,
          forceLawyerCta: resp.force_lawyer_cta,
          scene: resp.scene,
          messageId: resp.message_id ?? null,
          feedback: null,
          needSlots: resp.need_slots,
          waitingForSlot: resp.waiting_for_slot,
        };
        setMessages((prev) => [...prev, aiMsg]);
        setSlotPrompt(pickSlotPrompt(resp.need_slots, resp.waiting_for_slot));
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
    setSlotPrompt(null);
    try {
      const data = await api.sessionMessages(sessionId);
      const loaded = (data.messages ?? []).map((m) => {
        const rawId = (m as { id?: number | string }).id;
        const numericId = typeof rawId === "number" ? rawId : Number(rawId);
        return {
          ...m,
          id: rawId != null ? String(rawId) : nextId(),
          messageId: Number.isFinite(numericId) ? numericId : null,
          feedback: null,
        } as ChatMessage;
      });
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
    setSlotPrompt(null);
  }, []);

  const clearSlot = useCallback(() => {
    setSlotPrompt(null);
  }, []);

  return {
    messages,
    busy,
    activeSessionId,
    slotPrompt,
    send,
    loadSession,
    newSession,
    clearSlot,
  };
}
