// 合同审查（P2 占位）：导航可见，能力未开放

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractReviewStatus } from "../api/types";

export default function ContractReviewPanel() {
  const [status, setStatus] = useState<ContractReviewStatus | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .contractReviewStatus()
      .then(setStatus)
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, []);

  return (
    <div className="lead-panel contract-panel">
      <h2>合同审查</h2>
      <p className="muted">P2 规划能力：本期仅导航占位与接口预留，不提供自动审查结论。</p>

      <div className="opinion-result">
        <div className="opinion-watermark">即将开放 · 不构成法律意见</div>
        {err && <p className="form-msg error">{err}</p>}
        {status && (
          <>
            <div className="lead-meta">状态：{status.status}</div>
            <p className="law-excerpt">{status.message}</p>
            {status.planned_features?.length > 0 && (
              <section className="opinion-section">
                <h3>规划中的能力</h3>
                <ul className="event-list">
                  {status.planned_features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
        <div className="lawyer-form compact">
          <label>
            合同标题（预留）
            <input disabled placeholder="上传/粘贴后将在此填写" />
          </label>
          <label>
            合同正文摘录（预留）
            <textarea disabled rows={4} placeholder="能力开放后可粘贴条款文本" />
          </label>
          <button className="btn-primary" type="button" disabled>
            提交审查（未开放）
          </button>
        </div>
      </div>
    </div>
  );
}
