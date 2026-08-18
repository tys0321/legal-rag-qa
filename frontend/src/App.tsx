// 主应用：登录门禁（App）→ 主界面（MainView，按用户 key 强制重挂载）

import { useEffect, useState } from "react";
import { api, tokenStore } from "./api/client";
import AuthScreen from "./components/AuthScreen";
import MainView from "./components/MainView";

export default function App() {
  const [authed, setAuthed] = useState(() => !!tokenStore.get());

  // 登录态失效事件
  useEffect(() => {
    const handler = () => setAuthed(false);
    window.addEventListener("auth:expired", handler);
    return () => window.removeEventListener("auth:expired", handler);
  }, []);

  if (!authed) {
    return <AuthScreen onAuthed={() => setAuthed(true)} />;
  }

  const user = tokenStore.user();
  const userId = String(user?.user_id ?? "anon");

  const handleLogout = async () => {
    void api.logout();
    tokenStore.clear();
    setAuthed(false);
  };

  // key=userId：切换用户时整个 MainView 重新挂载，消息与会话缓存全部清零
  return (
    <MainView
      key={userId}
      userId={userId}
      username={user?.username ?? "用户"}
      isAdmin={tokenStore.isAdmin()}
      onLogout={handleLogout}
    />
  );
}
