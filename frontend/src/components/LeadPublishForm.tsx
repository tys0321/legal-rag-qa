// 用户发布案源需求

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LeadItem } from "../api/types";
import { contactError, isCnMobile } from "../utils/validation";

const SCENES = [
  "劳动用工",
  "房屋租赁",
  "婚姻家事",
  "交通事故",
  "消费维权",
  "行政诉讼",
  "合同纠纷",
];

interface Props {
  defaultScene?: string;
  onPublished?: (lead: LeadItem) => void;
}

export default function LeadPublishForm({ defaultScene = "劳动用工", onPublished }: Props) {
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [scene, setScene] = useState(defaultScene);
  const [region, setRegion] = useState("");
  const [contact, setContact] = useState("");
  const [firmVisible, setFirmVisible] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (defaultScene) setScene(defaultScene);
  }, [defaultScene]);

  const submit = async () => {
    const cErr = contactError(contact);
    if (cErr) {
      setMsg(cErr);
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      const lead = await api.createLead({
        title,
        summary,
        scene,
        region,
        contact: contact.trim(),
        firm_visible: firmVisible,
        allow_push: true,
        publish: true,
      });
      setMsg(`已发布案源 #${lead.id}，联系方式已脱敏为 ${lead.contact_masked}`);
      setTitle("");
      setSummary("");
      setContact("");
      onPublished?.(lead);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "发布失败");
    } finally {
      setBusy(false);
    }
  };

  const contactOk = !contactError(contact);
  const ready =
    title.trim().length >= 2 &&
    summary.trim().length >= 4 &&
    region.trim().length > 0 &&
    contactOk;

  return (
    <div className="lead-panel">
      <h2>发布案源需求</h2>
      <p className="muted">零收费演示闭环：发布后律师可按场景与地区匹配认领，并通过站内信/模拟中间号联系。</p>
      <div className="lawyer-form">
        <label>
          标题
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：拖欠工资两个月" />
        </label>
        <label>
          场景
          <select value={scene} onChange={(e) => setScene(e.target.value)}>
            {SCENES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          地区
          <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="如：北京市朝阳区" />
        </label>
        <label>
          案情摘要
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={4}
            placeholder="简要说明事实与诉求（勿填写敏感证件号）"
          />
        </label>
        <label>
          联系方式（手机须 11 位；将脱敏存储）
          <input
            value={contact}
            onChange={(e) => {
              const raw = e.target.value;
              // 纯数字按手机号限制 11 位
              setContact(/^\d*$/.test(raw) ? raw.slice(0, 11) : raw);
            }}
            placeholder="11 位手机号，或微信号"
            inputMode="tel"
          />
          {contact.trim() && contactError(contact) && (
            <span className="field-error">{contactError(contact)}</span>
          )}
          {contact.trim() && isCnMobile(contact) && (
            <span className="field-ok">手机号格式正确</span>
          )}
        </label>
        <label className="check-row">
          <input type="checkbox" checked={firmVisible} onChange={(e) => setFirmVisible(e.target.checked)} />
          允许认领律师所在律所成员查看（所内协作）
        </label>
        <button className="btn-primary" type="button" disabled={busy || !ready} onClick={() => void submit()}>
          {busy ? "发布中…" : "发布到案源广场"}
        </button>
        {!ready && !busy && (
          <p className="muted">需填写：标题（≥2字）、摘要（≥4字）、地区、有效联系方式（手机 11 位或微信号）。</p>
        )}
        {msg && <p className={`form-msg ${msg.includes("失败") ? "error" : ""}`}>{msg}</p>}
      </div>
    </div>
  );
}
