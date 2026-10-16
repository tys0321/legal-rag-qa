# 续作交接备忘

## 一句话进度

**M0–M7.2 已交付**：唯一管理员 `tys` + 离线混合检索 + 词面兜底。

## 怎么看产品

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d --build
```

浏览器：**http://127.0.0.1:8081/**（8080 是 Dify）

- 管理员：`tys`（唯一 admin，免律师认证）

## 检索

| 条件 | 行为 |
|---|---|
| 已有 `data/models/models--Qdrant--bge-small-zh-v1.5` | 离线混合检索 |
| 无模型缓存 | 词面扫描 `data/kb`（含 eval_core） |

## 评测

```bash
python scripts/run_eval_citations.py
```

## 管理员校正

```bash
python scripts/ensure_sole_admin.py
```
