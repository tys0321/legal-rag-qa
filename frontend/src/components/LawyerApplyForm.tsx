// 职业认证申请：律师 / 法官 / 检察官（省市区联动 + 擅长多选）

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { LawyerProfile, Profession } from "../api/types";
import chinaRegions from "../data/chinaRegions.json";

interface Props {
  profile: LawyerProfile | null;
  onUpdated: (p: LawyerProfile) => void;
}

type RegionTree = Record<string, Record<string, string[]>>;
const REGION_TREE = chinaRegions as RegionTree;
const PROVINCES = Object.keys(REGION_TREE);

const SPECS_BY_PROFESSION: Record<Profession, string[]> = {
  lawyer: [
    "劳动用工",
    "房屋租赁",
    "婚姻家事",
    "交通事故",
    "消费维权",
    "合同纠纷",
    "行政诉讼",
    "刑事辩护",
    "知识产权",
    "公司商事",
    "民间借贷",
    "医疗纠纷",
  ],
  judge: ["民商事", "刑事", "行政", "执行", "家事少年", "知识产权", "破产清算", "其他"],
  prosecutor: ["刑事公诉", "职务犯罪", "公益诉讼", "刑事执行检察", "未成年人检察", "控告申诉", "其他"],
};

const PROFESSION_OPTIONS: {
  id: Profession;
  label: string;
  idLabel: string;
  hint: string;
  defaultSpecs: string[];
}[] = [
  {
    id: "lawyer",
    label: "律师",
    idLabel: "执业证号",
    hint: "通过后可进入律师版：案源认领、意见书、合同审查。",
    defaultSpecs: ["劳动用工", "合同纠纷"],
  },
  {
    id: "judge",
    label: "法官",
    idLabel: "工作证号 / 单位编号",
    hint: "通过后进入审判辅助工作台：类案比对、法规效力检索（不开放接单）。",
    defaultSpecs: ["民商事"],
  },
  {
    id: "prosecutor",
    label: "检察官",
    idLabel: "工作证号 / 单位编号",
    hint: "通过后进入检察辅助工作台：构成要件检索、类案与文书（不开放接单）。",
    defaultSpecs: ["刑事公诉"],
  },
];

function parseRegion(raw: string): { province: string; city: string; district: string } {
  const text = (raw || "").trim();
  if (!text) return { province: "", city: "", district: "" };
  const parts = text.split(/[\s/·，,]+/).filter(Boolean);
  if (parts.length >= 3) {
    const [p, c, d] = parts;
    if (REGION_TREE[p]?.[c]?.includes(d)) return { province: p, city: c, district: d };
  }
  for (const province of PROVINCES) {
    if (!text.startsWith(province) && !province.startsWith(text.slice(0, 2))) continue;
    const cities = REGION_TREE[province] || {};
    for (const city of Object.keys(cities)) {
      for (const district of cities[city]) {
        if (text.includes(province) && text.includes(city) && text.includes(district)) {
          return { province, city, district };
        }
      }
    }
    if (text === province || text.startsWith(province)) {
      const city = Object.keys(cities)[0] || "";
      const district = (cities[city] || [])[0] || "";
      return { province, city, district };
    }
  }
  return { province: "北京市", city: "北京市", district: "朝阳区" };
}

function formatRegion(province: string, city: string, district: string): string {
  if (!province || !city || !district) return "";
  if (province === city) return `${province} ${district}`;
  return `${province} ${city} ${district}`;
}

export default function LawyerApplyForm({ profile, onUpdated }: Props) {
  const initialProf = (profile?.profession as Profession) || "lawyer";
  const initialRegion = parseRegion(profile?.region || "");
  const [profession, setProfession] = useState<Profession>(
    PROFESSION_OPTIONS.some((o) => o.id === initialProf) ? initialProf : "lawyer",
  );
  const [licenseNo, setLicenseNo] = useState(profile?.license_no || "");
  const [province, setProvince] = useState(initialRegion.province || "北京市");
  const [city, setCity] = useState(initialRegion.city || "北京市");
  const [district, setDistrict] = useState(initialRegion.district || "朝阳区");
  const [selectedSpecs, setSelectedSpecs] = useState<string[]>(() => {
    const fromProfile = (profile?.specialties || []).filter(Boolean);
    if (fromProfile.length) return fromProfile;
    return PROFESSION_OPTIONS.find((o) => o.id === initialProf)?.defaultSpecs || [];
  });
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const status = profile?.status || "none";
  const opt = PROFESSION_OPTIONS.find((o) => o.id === profession) || PROFESSION_OPTIONS[0];
  const specChoices = useMemo(() => SPECS_BY_PROFESSION[profession] || [], [profession]);
  const cities = useMemo(() => Object.keys(REGION_TREE[province] || {}), [province]);
  const districts = useMemo(() => REGION_TREE[province]?.[city] || [], [province, city]);
  const regionText = formatRegion(province, city, district);

  useEffect(() => {
    if (!cities.includes(city)) {
      const nextCity = cities[0] || "";
      setCity(nextCity);
      const nextDistricts = REGION_TREE[province]?.[nextCity] || [];
      setDistrict(nextDistricts[0] || "");
      return;
    }
    if (!districts.includes(district)) {
      setDistrict(districts[0] || "");
    }
  }, [province, city, cities, districts, district]);

  const pickProfession = (id: Profession) => {
    setProfession(id);
    const next = PROFESSION_OPTIONS.find((o) => o.id === id);
    const allowed = new Set(SPECS_BY_PROFESSION[id] || []);
    const kept = selectedSpecs.filter((s) => allowed.has(s));
    setSelectedSpecs(kept.length ? kept : next?.defaultSpecs || []);
  };

  const toggleSpec = (name: string) => {
    setSelectedSpecs((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name],
    );
  };

  const submit = async () => {
    if (!regionText || selectedSpecs.length === 0) {
      setMsg("请选择完整地区（省 / 市 / 区县）和至少一个业务方向");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      const specs = selectedSpecs;
      const hadFiles = files.length > 0;
      let p: LawyerProfile;
      if (hadFiles) {
        const form = new FormData();
        form.append("profession", profession);
        form.append("license_no", licenseNo.trim());
        form.append("region", regionText);
        form.append("specialties", JSON.stringify(specs));
        for (const f of files) form.append("files", f);
        p = await api.lawyerApply(form);
      } else {
        p = await api.lawyerApplyJson({
          profession,
          license_no: licenseNo,
          region: regionText,
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

          <div className="region-cascade">
            <div className="region-cascade-label">地区 / 单位所在地</div>
            <div className="region-cascade-row">
              <label>
                省 / 直辖市
                <select value={province} onChange={(e) => setProvince(e.target.value)}>
                  {PROVINCES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                市
                <select value={city} onChange={(e) => setCity(e.target.value)}>
                  {cities.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                区 / 县
                <select value={district} onChange={(e) => setDistrict(e.target.value)}>
                  {districts.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {regionText && <p className="muted region-preview">已选：{regionText}</p>}
          </div>

          <div className="spec-picker">
            <div className="spec-picker-label">
              擅长 / 业务方向
              <span className="muted">（可多选，已选 {selectedSpecs.length}）</span>
            </div>
            <div className="spec-chip-grid" role="group" aria-label="业务方向">
              {specChoices.map((name) => {
                const on = selectedSpecs.includes(name);
                return (
                  <button
                    key={name}
                    type="button"
                    className={`spec-chip ${on ? "active" : ""}`}
                    aria-pressed={on}
                    onClick={() => toggleSpec(name)}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="cert-upload">
            <div className="spec-picker-label">证明材料（执业证 / 工作证）</div>
            <p className="muted cert-upload-hint">支持 JPG / PNG / WEBP / PDF，可多选</p>
            <input
              ref={fileRef}
              type="file"
              className="cert-upload-input"
              accept=".jpg,.jpeg,.png,.pdf,.webp"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            <button
              type="button"
              className="cert-upload-btn"
              onClick={() => fileRef.current?.click()}
            >
              <span className="cert-upload-icon">＋</span>
              <span>{files.length ? "继续添加文件" : "点击上传证明材料"}</span>
            </button>
            {files.length > 0 && (
              <ul className="cert-file-list">
                {files.map((f) => (
                  <li key={`${f.name}-${f.size}-${f.lastModified}`}>
                    <span className="cert-file-name" title={f.name}>
                      {f.name}
                    </span>
                    <span className="cert-file-size">
                      {f.size < 1024 * 1024
                        ? `${Math.max(1, Math.round(f.size / 1024))} KB`
                        : `${(f.size / (1024 * 1024)).toFixed(1)} MB`}
                    </span>
                    <button
                      type="button"
                      className="cert-file-remove"
                      aria-label={`移除 ${f.name}`}
                      onClick={() => {
                        setFiles((prev) => prev.filter((x) => x !== f));
                        if (fileRef.current) fileRef.current.value = "";
                      }}
                    >
                      移除
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            className="btn-primary"
            type="button"
            disabled={
              busy ||
              licenseNo.trim().length < 4 ||
              !regionText ||
              selectedSpecs.length === 0
            }
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
