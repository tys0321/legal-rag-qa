# 续作交接备忘

## 一句话进度

**M0–M7 + 唯一管理员权限**已交付并 push。当前唯一管理员：`tys`（免律师认证，全功能）。

## 仓库

- 远程：`https://github.com/tys0321/legal-rag-qa`
- 最新相关提交：`8847535` feat(auth): sole admin tys with full access

## 怎么看产品

1. 先启动 Docker Desktop  
2. 再执行：

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d
```

3. 浏览器打开：**http://127.0.0.1:8081/**（8080 是 Dify，不要用）  
4. 用 **tys** 登录 → 退出再登一次以刷新权限

## 管理员规则

- 仅 `tys` 可为 admin（配置项 `SOLE_ADMIN_USERNAME`，默认 tys）
- 管理员：免律师认证、案源可写、免责视为已确认、管理后台全开
- 不可再把他人设为 admin；不可删除/降权 tys
- 校正脚本：`python scripts/ensure_sole_admin.py`

## 评测

```bash
python scripts/run_eval_citations.py
```
