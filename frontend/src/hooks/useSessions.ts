// 会话列表管理 hook：加载、新建、删除、选中

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { SessionItem } from "../api/types";

export interface SessionsController {
  sessions: SessionItem[];
  activeId: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  create: () => void;
  select: (id: string) => void;
  remove: (id: string) => Promise<void>;
}

export function useSessions(
  activeId: string | null,
  onSelect: (id: string) => void,
  onNew: () => void,
): SessionsController {
  const [sessions, setSessions] = useState<SessionItem[]>([]);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listSessions();
      setSessions(data.sessions);
    } catch {
      /* 忽略 */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // 会话变化事件（发送消息后刷新）
  useEffect(() => {
    const handler = () => void refresh();
    window.addEventListener("sessions:changed", handler);
    return () => window.removeEventListener("sessions:changed", handler);
  }, [refresh]);

  const create = useCallback(() => {
    onNew();
    void refresh();
  }, [onNew, refresh]);

  const select = useCallback(
    (id: string) => {
      onSelect(id);
    },
    [onSelect],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.deleteSession(id);
      await refresh();
    },
    [refresh],
  );

  return { sessions, activeId, loading: false, refresh, create, select, remove };
}
