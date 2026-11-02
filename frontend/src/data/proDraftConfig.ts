// 职业草稿：少字段、能填完、能出结果

import type { DraftMode } from "../api/types";

export type FieldDef = {
  key: string;
  label: string;
  placeholder: string;
  rows?: number;
  required?: boolean;
};

export type DraftConfig = {
  title: string;
  blurb: string;
  sceneLabel: string;
  scenes: string[];
  button: string;
  questionKey: string;
  fields: FieldDef[];
  sectionOrder: { key: string; label: string }[];
};

export const DRAFT_CONFIG: Record<DraftMode, DraftConfig> = {
  lawyer: {
    title: "法律意见书",
    blurb: "写清诉求和事实，生成带引用的意见书草稿。",
    sceneLabel: "类型",
    scenes: ["劳动用工", "房屋租赁", "婚姻家事", "交通事故", "消费维权", "行政诉讼", "合同纠纷"],
    button: "生成草稿",
    questionKey: "goal",
    fields: [
      {
        key: "goal",
        label: "要解决的问题",
        placeholder: "如：拖欠工资能否主张经济补偿？是否必须先仲裁？",
        rows: 2,
        required: true,
      },
      {
        key: "facts",
        label: "案情与证据",
        placeholder: "当事人、关键时间线、对方态度、手头证据（脱敏）",
        rows: 8,
        required: true,
      },
    ],
    sectionOrder: [
      { key: "case_summary", label: "案情梳理" },
      { key: "legal_analysis", label: "法律分析" },
      { key: "action_advice", label: "行动建议" },
      { key: "disclaimer", label: "免责声明" },
    ],
  },
  judge: {
    title: "争点与说理",
    blurb: "贴入诉请与答辩要点，整理争点和说理路径。",
    sceneLabel: "案由",
    scenes: ["合同纠纷", "劳动争议", "婚姻家事", "侵权责任", "房屋租赁", "行政诉讼", "其他民商事"],
    button: "生成草稿",
    questionKey: "focus",
    fields: [
      {
        key: "focus",
        label: "待决问题",
        placeholder: "如：违约金应否调整；诉讼时效是否经过",
        rows: 2,
        required: true,
      },
      {
        key: "pleadings",
        label: "诉请 · 答辩 · 事实",
        placeholder:
          "原告诉请：…\n被告答辩：…\n无争议事实：…\n争议事实：…",
        rows: 10,
        required: true,
      },
    ],
    sectionOrder: [
      { key: "case_summary", label: "事实要点" },
      { key: "issues", label: "争议焦点" },
      { key: "legal_analysis", label: "法律适用" },
      { key: "action_advice", label: "裁判思路" },
      { key: "disclaimer", label: "免责声明" },
    ],
  },
  prosecutor: {
    title: "审查报告",
    blurb: "写清事实、证据和焦点，生成审查要点草稿。",
    sceneLabel: "罪名/类型",
    scenes: ["盗窃", "诈骗", "故意伤害", "危险驾驶", "职务犯罪", "公益诉讼", "其他刑事"],
    button: "生成草稿",
    questionKey: "focus",
    fields: [
      {
        key: "focus",
        label: "审查焦点",
        placeholder: "如：是否达到起诉标准；此罪与彼罪如何界分",
        rows: 2,
        required: true,
      },
      {
        key: "dossier",
        label: "事实 · 证据 · 辩解",
        placeholder:
          "认定事实：…\n主要证据（及证明对象）：…\n辩解/缺口：…",
        rows: 10,
        required: true,
      },
    ],
    sectionOrder: [
      { key: "case_summary", label: "事实摘要" },
      { key: "evidence", label: "证据与证明" },
      { key: "legal_analysis", label: "定性分析" },
      { key: "action_advice", label: "处理意见" },
      { key: "disclaimer", label: "免责声明" },
    ],
  },
};
