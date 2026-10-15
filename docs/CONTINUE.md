# 续作交接备忘（复制到新对话即可）

## 一句话进度

法律 RAG 项目已完成 **M0–M4**、**M5.1–M5.3（意见书 / 文书×8 / 计算器×5）**；P1 工具线已交付待确认。

## 仓库与提交

- 路径：`c:\Users\64517\Desktop\leqal\legal-rag-qa`
- 远程 demo：`https://github.com/tys0321/legal-rag-qa`
- 本地领先 origin 若干 commit（可能未 push），关键：
  - `1279c87` feat(m0): MySQL + Docker Compose
  - `66c4da9` feat(m1): hybrid retrieval / rerank / critic
  - `e9335a6` feat(m2): lawyer auth / risk / slots / dual-mode UI
  - `c0e2ecf` feat(m3.1): leads publish / match / claim / simulated contact
  - `49c4037` feat(m3.2): lightweight firms + firm-visible leads
  - `582c8e3` feat(m3.3): leads plaza / publish / firm UI
  - `d75c8d8` feat(m4.1): laws search API + frontend panel
  - `896e4da` docs(m4.1): real hybrid smoke results
  - `1d3f236` feat(m4.2): cases search API + case cards UI
  - `98ae214` feat(m4.3): 52-scene catalog placeholders
  - `3806cc1` feat(m5.1): legal opinion draft via RAG+LLM
  - `630d39a` feat(m5.2): document templates ×8
  - （本轮）feat(m5.3): legal calculators ×5

## 已确认产品决策（摘要）

- 双端同期；律师上传执业证 + 管理员审核；pending 只读
- MVP 场景 7 类：劳动、租房、婚姻、交通事故、消费、行政诉讼、合同
- P0：问答/法规/类案/双端认证/案源闭环；P1：意见书+文书8+计算器5
- 知识库策略 D：国家级+核心法先入；地方法规默认不入
- RAG：BM25+向量+重排；引用准确率目标 ≥90%；历史 12 轮
- 合规：L1 强拦 / L2≥50 万转律师 / L3 正常；免责顶部+末尾+弹窗
- MySQL 业务库；Compose 用 Qdrant；差异化=引用可信+双端案源闭环
- 案源：零收费可演示闭环；匹配=场景/擅长+地区

## 文档位置

- PRD：`c:\Users\64517\Desktop\leqal\docs\PRD-产品需求文档.md`（另有 docx）
- 技术需求：`c:\Users\64517\Desktop\leqal\docs\技术需求文档.md`
- 模块说明：`legal-rag-qa/docs/M0|…|M5.3-交付说明.md`

## 新对话请直接粘贴

```
确认 M5.3。P1 工具线已完成；下一步请对照 PRD 做联调验收 / 部署说明，或进入 P2 合同审查占位。

基线仓库：c:\Users\64517\Desktop\leqal\legal-rag-qa
请先阅读 docs/CONTINUE.md、docs/M5.3-交付说明.md。
规则：每完成一个模块先提交并说明测试结果，等我确认后再做下一项。
```

## 本机启动提醒

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d mysql qdrant
```
