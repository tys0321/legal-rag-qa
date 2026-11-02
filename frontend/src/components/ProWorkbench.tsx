// 已认证法律从业者工作台：律师 / 法官 / 检察官差异化功能

import type { LawyerProfile } from "../api/types";
import type { ChatController } from "../hooks/useChat";
import LawyerPanel from "./LawyerPanel";
import JudgeWorkbench from "./JudgeWorkbench";
import ProsecutorWorkbench from "./ProsecutorWorkbench";

interface Props {
  profile: LawyerProfile | null;
  tab: string;
  chat: ChatController;
}

export default function ProWorkbench({ profile, tab, chat }: Props) {
  const profession = (profile?.profession || "lawyer").toLowerCase();

  if (profession === "judge") {
    return <JudgeWorkbench profile={profile} tab={tab} chat={chat} />;
  }
  if (profession === "prosecutor") {
    return <ProsecutorWorkbench profile={profile} tab={tab} chat={chat} />;
  }
  return <LawyerPanel profile={profile} tab={tab} chat={chat} />;
}
