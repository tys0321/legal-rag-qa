// 律师认证 + 案源广场 / 所内案源 / 轻量律所

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LawyerProfile } from "../api/types";
import LeadPlaza from "./LeadPlaza";
import FirmPanel from "./FirmPanel";

interface Props {
  readonlyMode: boolean;
}

type LawyerTab = "plaza" | "firm-leads" | "firm";

export default function LawyerPanel({ readonlyMode }: Props) {
  const [profile, setProfile] = useState<LawyerProfile | null>(null);
  const [licenseNo, setLicenseNo] = useState("");
  const [region, setRegion] = useState("");
  const [specialties, setSpecialties] = useState("劳动用工,合同纠纷");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState<LawyerTab>("plaza");

  const refresh = () => {
    api.lawyerStatus().then(setProfile).catch(() => undefined);
  };

  useEffect(() => {
    refresh();
  }, []);

  const submit = async () => {
    setBusy(true);
    setMsg("");
    try {
      const specs = specialties
        .split(/[,，]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const p = await api.lawyerApplyJson({
        license_no: licenseNo,
        region,
        specialties: specs,
      });
      setProfile(p);
      setMsg("已提交，等待管理员审核。审核前律师版为只读。");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  const status = profile?.status || "none";
  const canBrowse = status === "approved" || status === "pending";

  return (
    <div className="lawyer-panel wide">
      <h2>律师版</h2>
      {readonlyMode && (
        <div className="risk-banner warn inline">
          当前为<strong>待审只读</strong>：可浏览案源列表，不可认领或联系当事人。
        </div>
      )}
      <p className="muted">
        认证状态：<strong>{status}</strong>
        {profile?.reject_reason ? `（驳回原因：${profile.reject_reason}）` : ""}
        {status === "approved" && (
          <>
            {" "}
            · 擅长 {(profile?.specialties || []).join("、") || "未填"} · {profile?.region}
          </>
        )}
      </p>

      {status !== "approved" && (
        <div className="lawyer-form">
          <label>
            执业证号
            <input value={licenseNo} onChange={(e) => setLicenseNo(e.target.value)} placeholder="请输入执业证号" />
          </label>
          <label>
            执业地区
            <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="如：北京市" />
          </label>
          <label>
            擅长领域（逗号分隔）
            <input value={specialties} onChange={(e) => setSpecialties(e.target.value)} />
          </label>
          <button className="btn-primary" type="button" disabled={busy || !licenseNo || !region} onClick={() => void submit()}>
            {busy ? "提交中…" : "提交认证申请"}
          </button>
          {msg && <p className="form-msg">{msg}</p>}
        </div>
      )}

      {canBrowse && (
        <>
          <div className="sub-tabs">
            <button type="button" className={tab === "plaza" ? "active" : ""} onClick={() => setTab("plaza")}>
              案源广场
            </button>
            <button type="button" className={tab === "firm-leads" ? "active" : ""} onClick={() => setTab("firm-leads")}>
              所内案源
            </button>
            <button type="button" className={tab === "firm" ? "active" : ""} onClick={() => setTab("firm")}>
              轻量律所
            </button>
          </div>
          {tab === "plaza" && <LeadPlaza readonlyMode={readonlyMode || status !== "approved"} scope="plaza" />}
          {tab === "firm-leads" && <LeadPlaza readonlyMode={readonlyMode || status !== "approved"} scope="firm" />}
          {tab === "firm" && <FirmPanel readonlyMode={readonlyMode || status !== "approved"} />}
        </>
      )}
    </div>
  );
}
