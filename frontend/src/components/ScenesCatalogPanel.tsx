// 52 一级场景分类：MVP 激活 + 即将开放占位

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { SceneCatalogItem, SceneCatalogResult } from "../api/types";

interface Props {
  onPickActive?: (sceneId: string) => void;
}

export default function ScenesCatalogPanel({ onPickActive }: Props) {
  const [data, setData] = useState<SceneCatalogResult | null>(null);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "coming_soon">("all");

  useEffect(() => {
    api
      .listScenes()
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, []);

  const items = useMemo(() => {
    const list = data?.items || [];
    if (filter === "all") return list;
    return list.filter((x) => x.status === filter);
  }, [data, filter]);

  const byGroup = useMemo(() => {
    const map = new Map<string, SceneCatalogItem[]>();
    for (const it of items) {
      const g = it.group || "其他";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(it);
    }
    return [...map.entries()];
  }, [items]);

  return (
    <div className="lead-panel scenes-catalog">
      <h2>场景分类</h2>
      <p className="muted">
        对标 <strong>52</strong> 一级分类信息架构：当前开放{" "}
        <strong>{data?.active_count ?? 7}</strong> 类（MVP），其余「即将开放」占位。
      </p>
      {err && <p className="form-msg error">{err}</p>}
      {data && (
        <p className="muted">
          共 {data.total} 类 · 已开放 {data.active_count} · 即将开放 {data.coming_soon_count}
        </p>
      )}
      <div className="sub-tabs scene-filter">
        <button type="button" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>
          全部
        </button>
        <button type="button" className={filter === "active" ? "active" : ""} onClick={() => setFilter("active")}>
          已开放
        </button>
        <button
          type="button"
          className={filter === "coming_soon" ? "active" : ""}
          onClick={() => setFilter("coming_soon")}
        >
          即将开放
        </button>
      </div>

      {byGroup.map(([group, list]) => (
        <section key={group} className="scene-group">
          <h3>{group}</h3>
          <div className="scene-grid">
            {list.map((it) => {
              const active = it.status === "active";
              return (
                <button
                  key={it.id}
                  type="button"
                  className={`scene-chip ${active ? "active" : "soon"}`}
                  disabled={!active}
                  title={active ? `进入「${it.name}」相关咨询` : "即将开放"}
                  onClick={() => active && onPickActive?.(it.id)}
                >
                  <span className="scene-chip-name">{it.name}</span>
                  {!active && <span className="scene-chip-badge">即将开放</span>}
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
