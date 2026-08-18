// 登录 / 注册页面（含注册约束即时校验）

import { useState } from "react";
import { api, tokenStore } from "../api/client";

interface Props {
  onAuthed: () => void;
}

// 密码规则：至少 6 位，必须同时含字母和数字
const PASSWORD_MIN = 6;
const HAS_LETTER = /[A-Za-z]/;
const HAS_DIGIT = /\d/;

function passwordIssues(pwd: string): string[] {
  const issues: string[] = [];
  if (!pwd) issues.push("请输入密码");
  else {
    if (pwd.length < PASSWORD_MIN) issues.push(`至少 ${PASSWORD_MIN} 位`);
    if (!HAS_LETTER.test(pwd)) issues.push("需包含字母");
    if (!HAS_DIGIT.test(pwd)) issues.push("需包含数字");
  }
  return issues;
}

export default function AuthScreen({ onAuthed }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState({ username: false, password: false, confirm: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const nameOk = username.trim().length >= 2;
  const pwdIssues = mode === "register" ? passwordIssues(password) : [];
  const pwdOk = pwdIssues.length === 0;
  const confirmOk = confirm === password;
  const allOk = nameOk && pwdOk && (mode === "login" || confirmOk);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({ username: true, password: true, confirm: true });
    setError(null);
    if (!allOk) return;
    setBusy(true);
    try {
      const resp =
        mode === "login"
          ? await api.login(username.trim(), password)
          : await api.register(username.trim(), password);
      tokenStore.set(resp.token);
      tokenStore.saveUser({
        username: resp.username,
        user_id: resp.user_id,
        role: resp.role,
      });
      onAuthed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (m: "login" | "register") => {
    setMode(m);
    setError(null);
    setTouched({ username: false, password: false, confirm: false });
  };

  const showNameError = touched.username && !nameOk;
  const showPwdError = touched.password && !pwdOk;
  const showConfirmError = touched.confirm && !confirmOk;

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">⚖️</div>
        <h1>法律知识问答助手</h1>
        <p className="auth-sub">基于 RAG 检索增强生成 · 引用可溯源</p>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => switchMode("login")}
          >
            登录
          </button>
          <button
            className={`auth-tab ${mode === "register" ? "active" : ""}`}
            onClick={() => switchMode("register")}
          >
            注册
          </button>
        </div>

        <form onSubmit={submit} className="auth-form" noValidate>
          <label>
            用户名
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, username: true }))}
              placeholder="请输入用户名（至少 2 个字符）"
              className={showNameError ? "input-error" : ""}
              autoFocus
            />
            {showNameError && (
              <span className="field-hint err-text">
                {username.trim() ? "用户名至少 2 个字符" : "用户名不能为空"}
              </span>
            )}
          </label>

          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, password: true }))}
              placeholder={mode === "register" ? "至少 6 位，需含字母和数字" : "请输入密码"}
              className={showPwdError ? "input-error" : ""}
            />
            {mode === "register" && (
              <span className={`field-hint ${pwdOk && password ? "hint-ok" : ""}`}>
                {pwdOk && password
                  ? "✓ 密码符合要求"
                  : `密码需满足：${pwdIssues.join("、")}`}
              </span>
            )}
          </label>

          {mode === "register" && (
            <label>
              确认密码
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, confirm: true }))}
                placeholder="再次输入密码"
                className={showConfirmError ? "input-error" : ""}
              />
              {showConfirmError && (
                <span className="field-hint err-text">两次输入的密码不一致</span>
              )}
            </label>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button className="btn-primary auth-btn" disabled={busy || !allOk}>
            {busy ? "请稍候…" : mode === "login" ? "登 录" : "注 册"}
          </button>
        </form>

        <p className="auth-foot">
          ⚠️ AI 生成内容仅供参考，不构成正式法律意见。
        </p>
      </div>
    </div>
  );
}
