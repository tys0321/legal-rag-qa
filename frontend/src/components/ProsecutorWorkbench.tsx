// 检察官工作台（导航由主侧边栏控制）

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

export default function ProsecutorWorkbench({ profile, tab, chat }: Props) {
  return (
    <div className="lawyer-panel wide">
      <h2>检察官工作台</h2>
      <p className="muted">
        {(profile?.specialties || []).join("、") || "未填方向"}
        {profile?.region ? ` · ${profile.region}` : ""}
        · 不开放案源
      </p>
      {tab === "review" && <ProDraftPanel mode="prosecutor" />}
      {tab === "ask" && <ProAskPanel hint="检索构成要件与程序节点，回答带来源。" chat={chat} />}
      {tab === "cases" && <CasesSearchPanel />}
      {tab === "laws" && <LawsSearchPanel />}
      {tab === "templates" && <TemplatesPanel audience="prosecutor" title="检察文书模板" />}
      {tab === "calculators" && <CalculatorsPanel audience="prosecutor" title="办案期限" />}
    </div>
  );
}
