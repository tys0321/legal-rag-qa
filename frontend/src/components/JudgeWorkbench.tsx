// 法官工作台（导航由主侧边栏控制）

import type { LawyerProfile } from "../api/types";
import type { ChatController } from "../hooks/useChat";
import ProAskPanel from "./ProAskPanel";
import ProDraftPanel from "./ProDraftPanel";
import LawsSearchPanel from "./LawsSearchPanel";
import CasesSearchPanel from "./CasesSearchPanel";
import TemplatesPanel from "./TemplatesPanel";
import CalculatorsPanel from "./CalculatorsPanel";

interface Props {
  profile: LawyerProfile | null;
  tab: string;
  chat: ChatController;
}

export default function JudgeWorkbench({ profile, tab, chat }: Props) {
  return (
    <div className="lawyer-panel wide">
      <h2>法官工作台</h2>
      <p className="muted">
        {(profile?.specialties || []).join("、") || "未填方向"}
        {profile?.region ? ` · ${profile.region}` : ""}
        · 不开放案源
      </p>
      {tab === "docket" && <ProDraftPanel mode="judge" />}
      {tab === "ask" && <ProAskPanel hint="检索法条、程序节点与裁判口径，回答带来源。" chat={chat} />}
      {tab === "cases" && <CasesSearchPanel />}
      {tab === "laws" && <LawsSearchPanel />}
      {tab === "templates" && <TemplatesPanel audience="judge" title="裁判文书模板" />}
      {tab === "calculators" && <CalculatorsPanel audience="judge" title="期限 / 诉讼费" />}
    </div>
  );
}
