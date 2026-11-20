// 检察官工作台（导航由主侧边栏控制）

import { useState } from "react";
import type { LawyerProfile } from "../api/types";
import type { ChatController } from "../hooks/useChat";
import ProAskPanel from "./ProAskPanel";
import ProDraftPanel from "./ProDraftPanel";
import LawsSearchPanel from "./LawsSearchPanel";
import CasesSearchPanel from "./CasesSearchPanel";
import TemplatesPanel from "./TemplatesPanel";
import CalculatorsPanel from "./CalculatorsPanel";
import CaseWorkspacePanel from "./CaseWorkspacePanel";
import ElementsChecklist from "./ElementsChecklist";

interface Props {
  profile: LawyerProfile | null;
  tab: string;
  chat: ChatController;
}

export default function ProsecutorWorkbench({ profile, tab, chat }: Props) {
  const [seedValues, setSeedValues] = useState<Record<string, string> | undefined>();
  const [seedScene, setSeedScene] = useState<string | undefined>();
  const [draftKey, setDraftKey] = useState(0);

  return (
    <div className="lawyer-panel wide">
      <h2>检察官工作台</h2>
      <p className="muted">
        {(profile?.specialties || []).join("、") || "未填方向"}
        {profile?.region ? ` · ${profile.region}` : ""}
        · 不开放案源
      </p>
      {tab === "matters" && <CaseWorkspacePanel roleMode="prosecutor" />}
      {tab === "elements" && (
        <ElementsChecklist
          onFillDraft={(text, charge) => {
            setSeedValues({ supplement_hint: text });
            setSeedScene(charge);
            setDraftKey((k) => k + 1);
            window.dispatchEvent(
              new CustomEvent("app:toast", {
                detail: { message: "已准备填入审查报告，请切换到「审查报告」页", type: "success" },
              }),
            );
          }}
        />
      )}
      {tab === "review" && (
        <ProDraftPanel key={draftKey} mode="prosecutor" seedValues={seedValues} seedScene={seedScene} />
      )}
      {tab === "ask" && <ProAskPanel hint="检索构成要件与程序节点，回答带来源。" chat={chat} />}
      {tab === "cases" && <CasesSearchPanel />}
      {tab === "laws" && <LawsSearchPanel />}
      {tab === "templates" && <TemplatesPanel audience="prosecutor" title="检察文书模板" />}
      {tab === "calculators" && (
        <CalculatorsPanel audience="prosecutor" title="办案期限" roleMode="prosecutor" />
      )}
    </div>
  );
}
