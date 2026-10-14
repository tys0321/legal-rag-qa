// 律师认证申请 / 待审只读提示

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LawyerProfile } from "../api/types";

interface Props {
  readonlyMode: boolean;
}

export default function LawyerPanel({ readonlyMode }: Props) {
  const [profile, setProfile] = useState<LawyerProfile | null>(null);
  const [licenseNo, setLicenseNo] = useState("");
  const [region, setRegion] = useState("");
  const [specialties, setSpecialties] = useState("劳动用工,合同纠纷");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

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

  return (
    <div className="lawyer-panel">
      <h2>律师版</h2>
      {readonlyMode && (
        <div className="risk-banner warn">
          当前为<strong>待审只读</strong>：可浏览律师版界面，不可认领案源或联系当事人（写操作将在审核通过后开放）。
        </div>
      )}
      <p className="muted">
        认证状态：<strong>{status}</strong>
        {profile?.reject_reason ? `（驳回原因：${profile.reject_reason}）` : ""}
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

      {status === "approved" && (
        <div className="lawyer-ok">
          <p>认证已通过。案源广场与匹配闭环将在下一阶段（M3）开放。</p>
          <ul>
            <li>擅长：{(profile?.specialties || []).join("、") || "未填"}</li>
            <li>地区：{profile?.region}</li>
          </ul>
        </div>
      )}
    </div>
  );
}
