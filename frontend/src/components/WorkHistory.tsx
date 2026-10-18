// 文书 / 计算器 / 合同审查的个人记录

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { UserRecordItem } from "../api/types";

interface Props {
  kind: "template" | "calculator" | "contract";
  tick: number;
  onOpen: (payload: Record<string, unknown>) => void;
}

export default function WorkHistory({ kind, tick, onOpen }: Props) {
  const [items, setItems] = useState<UserRecordItem[]>([]);

  const refresh = () => {
    api
      .listRecords(kind)
      .then((r) => setItems(r.items))
      .catch(() => setItems([]));
  };

  useEffect(() => {
    refresh();
  }, [kind, tick]);

  const open = async (id: number) => {
    const row = await api.getRecord(id);
    onOpen(row.payload || {});
  };

  const remove = async (id: number) => {
    await api.deleteRecord(id);
    refresh();
  };

  if (items.length === 0) {
    return (
      <div className="work-history">
        <h3>我的记录</h3>
        <p className="muted">生成后会留在这里，刷新页面也能再打开。</p>
      </div>
    );
  }

  return (
    <div className="work-history">
      <h3>我的记录</h3>
      {items.map((it) => (
        <div className="work-history-item" key={it.id}>
          <button type="button" className="work-history-open" onClick={() => void open(it.id)}>
            <strong>{it.title}</strong>
            <span>{it.summary}</span>
            <span className="muted">{it.created_at}</span>
          </button>
          <button type="button" className="btn-sm btn-danger" onClick={() => void remove(it.id)}>
            删除
          </button>
        </div>
      ))}
    </div>
  );
}
