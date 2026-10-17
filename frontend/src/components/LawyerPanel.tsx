// 律师认证 + 案源广场 / 所内案源 / 轻量律所

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { LawyerProfile } from "../api/types";
import LeadPlaza from "./LeadPlaza";
import FirmPanel from "./FirmPanel";

interface Props {
  readonlyMode: boolean;
  /** 管理员免律师认证，直接全权限 */
  isAdmin?: boolean;
}

type LawyerTab = "plaza" | "firm-leads" | "firm";

export default function LawyerPanel({ readonlyMode, isAdmin = false }: Props) {
  const [profile, setProfile] = useState<LawyerProfile | null>(null);
  const [licenseNo, setLicenseNo] = useState("");
  const [region, setRegion] = useState("");
  const [specialties, setSpecialties] = useState("劳动用工,合同纠纷");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState<LawyerTab>("plaza");
  const fileRef = useRef<HTMLInputElement>(null);

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
      const hadFiles = files.length > 0;
      let p: LawyerProfile;
      if (hadFiles) {
        const form = new FormData();
        form.append("license_no", licenseNo.trim());
        form.append("region", region.trim());
        form.append("specialties", JSON.stringify(specs));
        for (const f of files) form.append("files", f);
        p = await api.lawyerApply(form);
      } else {
        p = await api.lawyerApplyJson({
          license_no: licenseNo,
          region,
          specialties: specs,
        });
      }
      setProfile(p);
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      setMsg(
        hadFiles || (p.license_files || []).length > 0
          ? "已提交材料，等待管理员审核。审核前律师版为只读。"
          : "已提交（未附证照文件），等待管理员审核。建议补传执业证照片/PDF。",
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  const status = isAdmin ? "approved" : profile?.status || "none";
  const canBrowse = isAdmin || status === "approved" || status === "pending";
  const fullAccess = isAdmin || status === "approved";
  const effectiveReadonly = isAdmin ? false : readonlyMode;

  return (
    <div className="lawyer-panel wide">
      <h2>律师版</h2>
      {isAdmin && (
        <div className="risk-banner warn inline" style={{ borderColor: "var(--gold)", color: "var(--text)" }}>
          当前为<strong>管理员</strong>：无需律师认证，可使用案源认领、联系、律所等全部功能。
        </div>
      )}
      {effectiveReadonly && (
        <div className="risk-banner warn inline">
          当前为<strong>待审只读</strong>：可浏览案源列表，不可认领或联系当事人。
        </div>
      )}
      <p className="muted">
        认证状态：<strong>{isAdmin ? "管理员（免认证）" : status}</strong>
        {!isAdmin && profile?.reject_reason ? `（驳回原因：${profile.reject_reason}）` : ""}
        {fullAccess && !isAdmin && (
          <>
            {" "}
            · 擅长 {(profile?.specialties || []).join("、") || "未填"} · {profile?.region}
          </>
        )}
      </p>

      {!isAdmin && status !== "approved" && (
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
          <label>
            执业证材料（jpg / png / pdf，可多选）
            <input
              ref={fileRef}
              type="file"
              accept=".jpg,.jpeg,.png,.pdf,.webp"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
          </label>
          {files.length > 0 && (
            <p className="field-hint">已选 {files.length} 个文件：{files.map((f) => f.name).join("、")}</p>
          )}
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
          {tab === "plaza" && <LeadPlaza readonlyMode={effectiveReadonly || !fullAccess} scope="plaza" />}
          {tab === "firm-leads" && <LeadPlaza readonlyMode={effectiveReadonly || !fullAccess} scope="firm" />}
          {tab === "firm" && <FirmPanel readonlyMode={effectiveReadonly || !fullAccess} />}
        </>
      )}
    </div>
  );
}
