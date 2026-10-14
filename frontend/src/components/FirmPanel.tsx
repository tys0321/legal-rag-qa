// 轻量律所：创建 / 邀请成员

import { useEffect, useState } from "react";
import { api, tokenStore } from "../api/client";
import type { FirmInfo } from "../api/types";

interface Props {
  readonlyMode: boolean;
}

export default function FirmPanel({ readonlyMode }: Props) {
  const [firm, setFirm] = useState<FirmInfo | null>(null);
  const [name, setName] = useState("");
  const [invitee, setInvitee] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [missing, setMissing] = useState(false);

  const refresh = () => {
    api
      .myFirm()
      .then((f) => {
        setFirm(f);
        setMissing(false);
      })
      .catch(() => {
        setFirm(null);
        setMissing(true);
      });
  };

  useEffect(() => {
    refresh();
  }, []);

  const create = async () => {
    if (readonlyMode) return;
    setBusy(true);
    setMsg("");
    try {
      const f = await api.createFirm(name);
      setFirm(f);
      setMissing(false);
      setMsg("律所已创建");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "创建失败");
    } finally {
      setBusy(false);
    }
  };

  const invite = async () => {
    if (!firm || readonlyMode) return;
    setBusy(true);
    setMsg("");
    try {
      await api.inviteFirmMember(firm.id, invitee.trim());
      setInvitee("");
      refresh();
      setMsg("已邀请成员");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "邀请失败");
    } finally {
      setBusy(false);
    }
  };

  const myId = tokenStore.user()?.user_id;
  const isOwner = !!firm && myId != null && firm.owner_user_id === myId;

  return (
    <div className="firm-panel">
      <h3>轻量律所</h3>
      {msg && <p className="form-msg">{msg}</p>}

      {missing && !readonlyMode && (
        <div className="lawyer-form">
          <p className="muted">尚未加入律所。创建后可邀请成员并查看所内共享案源。</p>
          <label>
            律所名称
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：示例联合律所" />
          </label>
          <button className="btn-primary" type="button" disabled={busy || name.trim().length < 2} onClick={() => void create()}>
            创建律所
          </button>
        </div>
      )}

      {missing && readonlyMode && <p className="muted">审核通过后方可创建或加入律所。</p>}

      {firm && (
        <div className="firm-card">
          <p>
            <strong>{firm.name}</strong>
            <span className="muted"> · #{firm.id}</span>
          </p>
          <ul className="member-list">
            {firm.members.map((m) => (
              <li key={m.user_id}>
                {m.username} <span className="status-pill">{m.role}</span>
              </li>
            ))}
          </ul>
          {isOwner && !readonlyMode && (
            <div className="lawyer-form compact">
              <label>
                邀请成员（用户名）
                <input value={invitee} onChange={(e) => setInvitee(e.target.value)} placeholder="已注册用户名" />
              </label>
              <button className="btn-primary" type="button" disabled={busy || !invitee.trim()} onClick={() => void invite()}>
                邀请加入
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
