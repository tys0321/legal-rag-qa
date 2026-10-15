# 续作交接备忘（复制到新对话即可）

## 一句话进度

法律 RAG 项目已完成 **M0–M5（含 P1 工具）**；**M6（合同审查占位 + 部署/验收文档）已交付待确认**。MVP 功能线基本收口。

## 仓库与提交

- 路径：`c:\Users\64517\Desktop\leqal\legal-rag-qa`
- 远程 demo：`https://github.com/tys0321/legal-rag-qa`
- 本地领先 origin 若干 commit（可能未 push），关键：
  - `…` M0–M4 见历史
  - `3806cc1` feat(m5.1): legal opinion draft via RAG+LLM
  - `630d39a` feat(m5.2): document templates ×8
  - `94d268c` feat(m5.3): legal calculators ×5
  - `fb6e898` feat(m6): contract review placeholder + deploy/acceptance docs

## 已确认产品决策（摘要）

- 双端同期；律师上传执业证 + 管理员审核；pending 只读
- MVP 场景 7 类：劳动、租房、婚姻、交通事故、消费、行政诉讼、合同
- P0：问答/法规/类案/双端认证/案源闭环；P1：意见书+文书8+计算器5
- P2：合同审查本期仅占位；全量文书/计算器/地方法规规模化入库后续
- 知识库策略 D：国家级+核心法先入；地方法规默认不入
- RAG：BM25+向量+重排；引用准确率目标 ≥90%；历史 12 轮
- 合规：L1 强拦 / L2≥50 万转律师 / L3 正常；免责顶部+末尾+弹窗
- MySQL 业务库；Compose 用 Qdrant；差异化=引用可信+双端案源闭环

## 文档位置

- PRD：`c:\Users\64517\Desktop\leqal\docs\PRD-产品需求文档.md`
- 技术需求：`c:\Users\64517\Desktop\leqal\docs\技术需求文档.md`
- 部署：`legal-rag-qa/docs/DEPLOY.md`
- 模块说明：`legal-rag-qa/docs/M0|…|M6-交付说明.md`

## 新对话请直接粘贴

```
确认 M6。下一步可选：
1) push 远程并做一次 Compose 全栈烟测；
2) 补齐七场景评测集与引用准确率报告；
3) 消息反馈（有用/无用）与管理端反馈列表（技术文档 P0 项若仍缺）。

基线仓库：c:\Users\64517\Desktop\leqal\legal-rag-qa
请先阅读 docs/CONTINUE.md、docs/M6-交付说明.md、docs/DEPLOY.md。
```

## 本机启动提醒

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d mysql qdrant
```

详见 `docs/DEPLOY.md`。
