// 职业认证申请：律师 / 法官 / 检察官（审核通过后进入对应工作台）

import { useRef, useState } from "react";
import { api } from "../api/client";
import type { LawyerProfile, Profession } from "../api/types";

interface Props {
  profile: LawyerProfile | null;
  onUpdated: (p: LawyerProfile) => void;
}

const PROFESSION_OPTIONS: {
  id: Profession;
  label: string;
  idLabel: string;
  hint: string;
  specs: string;
}[] = [
  {
    id: "lawyer",
    label: "律师",
    idLabel: "执业证号",
    hint: "通过后可进入律师版：案源认领、意见书、合同审查。",
    specs: "劳动用工,合同纠纷",
  },
  {
    id: "judge",
    label: "法官",
    idLabel: "工作证号 / 单位编号",
    hint: "通过后进入审判辅助工作台：类案比对、法规效力检索（不开放接单）。",
    specs: "民商事,刑事,行政",
  },
  {
    id: "prosecutor",
    label: "检察官",
    idLabel: "工作证号 / 单位编号",
    hint: "通过后进入检察辅助工作台：构成要件检索、类案与文书（不开放接单）。",
    specs: "刑事公诉,职务犯罪,公益诉讼",
  },
];

export default function LawyerApplyForm({ profile, onUpdated }: Props) {
  const initialProf = (profile?.profession as Profession) || "lawyer";
  const [profession, setProfession] = useState<Profession>(
    PROFESSION_OPTIONS.some((o) => o.id === initialProf) ? initialProf : "lawyer",
  );
  const [licenseNo, setLicenseNo] = useState(profile?.license_no || "");
  const [region, setRegion] = useState(profile?.region || "");
  const [specialties, setSpecialties] = useState(
    (profile?.specialties || []).join(",") ||
      PROFESSION_OPTIONS.find((o) => o.id === initialProf)?.specs ||
      "劳动用工,合同纠纷",
  );
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const status = profile?.status || "none";
  const opt = PROFESSION_OPTIONS.find((o) => o.id === profession) || PROFESSION_OPTIONS[0];

  const pickProfession = (id: Profession) => {
    setProfession(id);
    const next = PROFESSION_OPTIONS.find((o) => o.id === id);
    if (next && !(profile?.specialties || []).length) {
      setSpecialties(next.specs);
    }
  };

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
        form.append("profession", profession);
        form.append("license_no", licenseNo.trim());
        form.append("region", region.trim());
        form.append("specialties", JSON.stringify(specs));
        for (const f of files) form.append("files", f);
        p = await api.lawyerApply(form);
      } else {
        p = await api.lawyerApplyJson({
          profession,
          license_no: licenseNo,
          region,
          specialties: specs,
        });
      }
      onUpdated(p);
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      setMsg(
        hadFiles || (p.license_files || []).length > 0
          ? `已提交${opt.label}认证材料，等待管理员审核。通过后本账号将进入${opt.label}工作台。`
          : "已提交（未附证明文件），等待审核。建议补传工作证/执业证照片或 PDF。",
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lawyer-panel wide">
      <h2>职业认证</h2>
      <p className="muted">
        面向律师、法官、检察官等法律从业者。认证通过后账号固定进入对应工作台，普通用户功能入口将不再显示。
      </p>
      <p className="muted">
        当前状态：<strong>{status}</strong>
        {profile?.profession ? ` · 申请职业 ${profile.profession}` : ""}
        {profile?.reject_reason ? `（驳回原因：${profile.reject_reason}）` : ""}
      </p>
      {status === "pending" && (
        <div className="risk-banner warn inline">材料审核中，通过后登录将自动进入对应职业界面。</div>
      )}
      {status === "rejected" && (
        <div className="risk-banner danger inline">上次申请未通过，可修改材料后重新提交。</div>
      )}
      {status !== "pending" && (
        <div className="lawyer-form">
          <div className="profession-picker" role="radiogroup" aria-label="申请职业">
            {PROFESSION_OPTIONS.map((o) => (
              <button
                key={o.id}
                type="button"
                className={`profession-chip ${profession === o.id ? "active" : ""}`}
                onClick={() => pickProfession(o.id)}
              >
                <strong>{o.label}</strong>
                <span>{o.hint}</span>
              </button>
            ))}
          </div>
          <p className="muted">{opt.hint}</p>
          <label>
            {opt.idLabel}
            <input
              value={licenseNo}
              onChange={(e) => setLicenseNo(e.target.value)}
              placeholder={profession === "lawyer" ? "如：京 A12345678901" : "单位核发编号（可脱敏）"}
            />
          </label>
          <label>
            地区 / 单位所在地
            <input
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              placeholder="如：北京市"
            />
          </label>
          <label>
            擅长 / 业务方向（逗号分隔）
            <input
              value={specialties}
              onChange={(e) => setSpecialties(e.target.value)}
              placeholder={opt.specs}
            />
          </label>
          <label>
            证明材料（执业证 / 工作证，图片或 PDF）
            <input
              ref={fileRef}
              type="file"
              accept=".jpg,.jpeg,.png,.pdf,.webp"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
          </label>
          <button
            className="btn-primary"
            type="button"
            disabled={busy || licenseNo.trim().length < 4 || region.trim().length < 2}
            onClick={() => void submit()}
          >
            {busy ? "提交中…" : `提交${opt.label}认证`}
          </button>
        </div>
      )}
      {msg && <p className="form-msg">{msg}</p>}
    </div>
  );
}
