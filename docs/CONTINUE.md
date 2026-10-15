# 续作交接备忘（复制到新对话即可）

## 一句话进度

法律 RAG 项目已完成 **M0–M3**，当前交付 **M4.1（法规检索页，真实混合检索）待确认**；下一步 **M4.2 类案卡 → M4.3 52 场景占位 → M5 P1 工具**。

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
  - （待推）feat(m4.1): laws search API + frontend panel

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
- 模块说明：`legal-rag-qa/docs/M0|M1|M2-交付说明.md`

## 新对话请直接粘贴

```
确认 M4.1，继续 M4.2（类案卡：API + 前端展示）。

基线仓库：c:\Users\64517\Desktop\leqal\legal-rag-qa
请先阅读 docs/CONTINUE.md、docs/M4.1-交付说明.md，并对照 leqal/docs/PRD-产品需求文档.md。
规则：每完成一个模块先提交并说明测试结果，等我确认后再做下一项；技术栈截图项（RAG/LLM/Python/Web/MySQL/向量检索）必须真实使用。
```

## 本机启动提醒

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d mysql qdrant
```
