# 续作交接备忘

## 一句话进度

**M0–M7 已交付并 push**；**M7.1 评测烟测已过**（lexical 35/35）。向量全量入库需本机 BGE 模型缓存（勿再卡在 HF 离线下载）。

## 仓库

- 远程：`https://github.com/tys0321/legal-rag-qa`
- 本地：`c:\Users\64517\Desktop\leqal\legal-rag-qa`

## 常用命令

```bash
# 健康检查
curl http://127.0.0.1:8000/api/health

# 七场景评测（无需嵌入）
python scripts/run_eval_citations.py
```

## 可选下一步

1. 准备好 `backend/data/models` 后小批量入库，再跑 `--mode retrieval`
2. Web 改端口避开 8080 冲突
3. 真实用户对话抽检引用准确率
