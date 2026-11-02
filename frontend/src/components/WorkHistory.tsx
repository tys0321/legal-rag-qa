// 文书 / 计算器 / 合同审查 / 意见书草稿的个人记录（分页 + 搜索）

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { UserRecordItem, UserRecordKind } from "../api/types";

interface Props {
  kind: UserRecordKind;
  tick: number;
  activeId?: number | null;
  onOpen: (payload: Record<string, unknown>, meta: { id: number; title: string }) => void;
}

const PAGE_SIZE = 8;

function formatTime(raw: string): string {
  const s = String(raw || "").replace("T", " ");
  return s.length >= 16 ? s.slice(0, 16) : s;
}

export default function WorkHistory({ kind, tick, activeId = null, onOpen }: Props) {
  const [items, setItems] = useState<UserRecordItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [err, setErr] = useState("");

  const refresh = (nextPage = page, nextQ = q) => {
    setBusy(true);
    setErr("");
    api
      .listRecords(kind, { page: nextPage, pageSize: PAGE_SIZE, q: nextQ })
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
        setPage(r.page);
        setPageCount(r.page_count);
      })
      .catch((e) => {
        setItems([]);
        setTotal(0);
        setErr(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => setBusy(false));
  };

  useEffect(() => {
    setPage(1);
    refresh(1, q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, tick]);

  const search = () => {
    const next = draft.trim();
    setQ(next);
    setPage(1);
    refresh(1, next);
  };

  const open = async (id: number, title: string) => {
    setOpeningId(id);
    setErr("");
    try {
      const row = await api.getRecord(id);
      const payload = row.payload || {};
      if (!payload || (typeof payload === "object" && !Object.keys(payload).length)) {
        setErr("该记录内容为空，无法打开");
        return;
      }
      onOpen(payload, { id, title: row.title || title });
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: `已打开「${row.title || title}」`, type: "success" },
        }),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "打开失败");
    } finally {
      setOpeningId(null);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.deleteRecord(id);
      const nextPage = items.length <= 1 && page > 1 ? page - 1 : page;
      setPage(nextPage);
      refresh(nextPage, q);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "删除失败");
    }
  };

  const clearAll = async () => {
    if (total === 0) return;
    if (!confirm(`确定清空当前类型的全部 ${total} 条记录？此操作不可恢复。`)) return;
    try {
      await api.clearRecords(kind);
      setQ("");
      setDraft("");
      setPage(1);
      refresh(1, "");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "清空失败");
    }
  };

  return (
    <section className="work-history">
      <header className="work-history-head">
        <div className="work-history-title">
          <h3>我的记录</h3>
          {total > 0 && <span className="work-history-count">{total}</span>}
        </div>
        {total > 0 && (
          <button type="button" className="work-history-clear" onClick={() => void clearAll()}>
            清空
          </button>
        )}
      </header>

      <div className="work-history-tools">
        <div className="work-history-search">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") search();
            }}
            placeholder="搜索标题或摘要"
            aria-label="搜索记录"
          />
          {draft && (
            <button
              type="button"
              className="work-history-clear-input"
              aria-label="清除"
              onClick={() => {
                setDraft("");
                if (q) {
                  setQ("");
                  setPage(1);
                  refresh(1, "");
                }
              }}
            >
              ×
            </button>
          )}
        </div>
        <button type="button" className="work-history-search-btn" onClick={search} disabled={busy}>
          搜索
        </button>
      </div>

      {err && <p className="form-msg error">{err}</p>}

      {items.length === 0 ? (
        <div className="work-history-empty">
          <p>
            {busy
              ? "加载中…"
              : q
                ? "没有匹配的记录"
                : "生成结果会出现在这里，可随时回看"}
          </p>
        </div>
      ) : (
        <ul className="work-history-list">
          {items.map((it) => (
            <li className="work-history-item" key={it.id}>
              <button
                type="button"
                className={`work-history-open ${activeId === it.id ? "active" : ""}`}
                disabled={openingId === it.id}
                onClick={() => void open(it.id, it.title)}
              >
                <span className="wh-title">{it.title}</span>
                <span className="wh-summary">
                  {openingId === it.id ? "打开中…" : it.summary || "—"}
                </span>
                <span className="wh-time">{formatTime(it.created_at)}</span>
              </button>
              <button
                type="button"
                className="work-history-del"
                title="删除"
                onClick={() => void remove(it.id)}
              >
                删除
              </button>
            </li>
          ))}
        </ul>
      )}

      {total > PAGE_SIZE && (
        <footer className="work-history-pager">
          <button
            type="button"
            disabled={busy || page <= 1}
            onClick={() => {
              const p = page - 1;
              setPage(p);
              refresh(p, q);
            }}
          >
            上一页
          </button>
          <span>
            {page} / {pageCount}
          </span>
          <button
            type="button"
            disabled={busy || page >= pageCount}
            onClick={() => {
              const p = page + 1;
              setPage(p);
              refresh(p, q);
            }}
          >
            下一页
          </button>
        </footer>
      )}
    </section>
  );
}
