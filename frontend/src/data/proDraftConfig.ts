// 职业草稿：少字段、能填完、能出结果

import type { DraftMode } from "../api/types";

export type FieldDef = {
  key: string;
  label: string;
  placeholder: string;
  rows?: number;
  required?: boolean;
  /** judge 诉辩对照双栏：left=诉请侧 right=答辩侧 */
  column?: "left" | "right" | "full";
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
  layout?: "default" | "pleadings";
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
    blurb: "对照诉请与答辩，整理争点、说理路径与庭审提纲。",
    sceneLabel: "案由",
    scenes: ["合同纠纷", "劳动争议", "婚姻家事", "侵权责任", "房屋租赁", "行政诉讼", "其他民商事"],
    button: "生成草稿",
    questionKey: "focus",
    layout: "pleadings",
    fields: [
      {
        key: "focus",
        label: "待决问题",
        placeholder: "如：违约金应否调整；诉讼时效是否经过",
        rows: 2,
        required: true,
        column: "full",
      },
      {
        key: "claim",
        label: "原告诉请",
        placeholder: "逐项列明诉讼请求…",
        rows: 5,
        required: true,
        column: "left",
      },
      {
        key: "defense",
        label: "被告答辩",
        placeholder: "主要抗辩与事实主张…",
        rows: 5,
        required: true,
        column: "right",
      },
      {
        key: "undisputed",
        label: "无争议事实",
        placeholder: "双方均认可或可初步认定的事实…",
        rows: 4,
        required: false,
        column: "left",
      },
      {
        key: "disputed",
        label: "争议事实",
        placeholder: "待证事实与举证情况…",
        rows: 4,
        required: false,
        column: "right",
      },
    ],
    sectionOrder: [
      { key: "case_summary", label: "事实要点" },
      { key: "issues", label: "争议焦点" },
      { key: "legal_analysis", label: "法律适用" },
      { key: "action_advice", label: "裁判思路" },
      { key: "hearing_outline", label: "庭审提纲" },
      { key: "disclaimer", label: "免责声明" },
    ],
  },
  prosecutor: {
    title: "审查报告",
    blurb: "写清事实、证据和焦点，生成审查要点与补查提纲。",
    sceneLabel: "罪名/类型",
    scenes: [
      "盗窃",
      "诈骗",
      "合同诈骗",
      "故意伤害",
      "抢劫",
      "危险驾驶",
      "交通肇事",
      "帮助信息网络犯罪活动",
      "非法吸收公众存款",
      "贪污",
      "受贿",
      "寻衅滋事",
      "公益诉讼（行政）",
      "其他刑事",
    ],
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
      {
        key: "supplement_hint",
        label: "要件/补侦提示（可选）",
        placeholder: "可从「构成要件」页勾选后一键填入",
        rows: 4,
        required: false,
      },
    ],
    sectionOrder: [
      { key: "case_summary", label: "事实摘要" },
      { key: "evidence", label: "证据与证明" },
      { key: "legal_analysis", label: "定性分析" },
      { key: "action_advice", label: "处理意见" },
      { key: "supplement", label: "补查提纲" },
      { key: "disclaimer", label: "免责声明" },
    ],
  },
};
