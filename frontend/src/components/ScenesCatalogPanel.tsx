// 52 一级场景分类（全部已开放）

import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { SceneCatalogItem, SceneCatalogResult } from "../api/types";

interface Props {
  onPickActive?: (sceneId: string) => void;
}

export default function ScenesCatalogPanel({ onPickActive }: Props) {
  const [data, setData] = useState<SceneCatalogResult | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listScenes()
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, []);

  const byGroup = useMemo(() => {
    const map = new Map<string, SceneCatalogItem[]>();
    for (const it of data?.items || []) {
      const g = it.group || "其他";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(it);
    }
    return [...map.entries()];
  }, [data]);

  return (
    <div className="lead-panel scenes-catalog">
      <h2>场景分类</h2>
      <p className="muted">
        对标 <strong>{data?.total ?? 52}</strong> 一级分类，全部可点进对应咨询。
      </p>
      {err && <p className="form-msg error">{err}</p>}

      {byGroup.map(([group, list]) => (
        <section key={group} className="scene-group">
          <h3>{group}</h3>
          <div className="scene-grid">
            {list.map((it) => (
              <button
                key={it.id}
                type="button"
                className="scene-chip active"
                title={`进入「${it.name}」相关咨询`}
                onClick={() => onPickActive?.(it.id)}
              >
                <span className="scene-chip-name">{it.name}</span>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
