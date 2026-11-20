// 律师工作台（导航由主侧边栏控制）

import type { LawyerProfile } from "../api/types";
import type { ChatController } from "../hooks/useChat";
import LeadPlaza from "./LeadPlaza";
import FirmPanel from "./FirmPanel";
import ProDraftPanel from "./ProDraftPanel";
import ContractReviewPanel from "./ContractReviewPanel";
import ProAskPanel from "./ProAskPanel";
import LawsSearchPanel from "./LawsSearchPanel";
import CasesSearchPanel from "./CasesSearchPanel";
import TemplatesPanel from "./TemplatesPanel";
import CalculatorsPanel from "./CalculatorsPanel";
import CaseWorkspacePanel from "./CaseWorkspacePanel";
import { useState } from "react";

interface Props {
  profile: LawyerProfile | null;
  tab: string;
  chat: ChatController;
}

export default function LawyerPanel({ profile, tab, chat }: Props) {
  const [leadScope, setLeadScope] = useState<"plaza" | "firm">("plaza");

  return (
    <div className="lawyer-panel wide">
      <h2>律师工作台</h2>
      <p className="muted">
        {(profile?.specialties || []).join("、") || "未填擅长"}
        {profile?.region ? ` · ${profile.region}` : ""}
      </p>

      {tab === "matters" && <CaseWorkspacePanel roleMode="lawyer" />}
      {tab === "leads" && (
        <div className="lead-panel">
          <div className="sub-tabs scene-filter">
            <button
              type="button"
              className={leadScope === "plaza" ? "active" : ""}
              onClick={() => setLeadScope("plaza")}
            >
              广场
            </button>
            <button
              type="button"
              className={leadScope === "firm" ? "active" : ""}
              onClick={() => setLeadScope("firm")}
            >
              所内
            </button>
          </div>
          <LeadPlaza readonlyMode={false} scope={leadScope} />
        </div>
      )}
      {tab === "ask" && <ProAskPanel hint="检索法条、要件与期限，回答带来源。" chat={chat} />}
      {tab === "opinion" && <ProDraftPanel mode="lawyer" />}
      {tab === "contracts" && <ContractReviewPanel />}
      {tab === "laws" && <LawsSearchPanel />}
      {tab === "cases" && <CasesSearchPanel />}
      {tab === "templates" && <TemplatesPanel audience="lawyer" title="文书模板" />}
      {tab === "calculators" && <CalculatorsPanel audience="lawyer" title="计算器" roleMode="lawyer" />}
      {tab === "firm" && <FirmPanel readonlyMode={false} />}
    </div>
  );
}
