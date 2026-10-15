# 部署说明（本机开发 + Docker Compose）

## 一、本机开发（推荐联调）

### 1. 依赖服务

```bash
cd c:\Users\64517\Desktop\leqal\legal-rag-qa
docker compose -f deploy/docker-compose.yml up -d mysql qdrant
```

### 2. 环境变量

在仓库根目录配置 `.env`（勿提交）：

```env
DEEPSEEK_API_KEY=sk-...
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=legal
MYSQL_PASSWORD=legal_pass
MYSQL_DATABASE=legal_rag
VECTOR_BACKEND=local
# 或 VECTOR_BACKEND=qdrant 且 QDRANT_URL=http://127.0.0.1:6333
```

### 3. 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/health`

### 4. 前端（开发代理）

```bash
cd frontend
npm install
npm run dev
```

生产构建并由后端托管：

```bash
cd frontend
npm run build
# 然后只起后端即可访问 http://127.0.0.1:8000/
```

## 二、Compose 全栈（Web + API + MySQL + Qdrant）

在仓库根目录准备 `.env`（至少 `DEEPSEEK_API_KEY`），然后：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

| 服务 | 端口 |
|---|---|
| Web (Nginx) | http://127.0.0.1:8080 |
| API | http://127.0.0.1:8000 |
| MySQL | 3306 |
| Qdrant | 6333 |

停止：

```bash
docker compose -f deploy/docker-compose.yml down
```

## 三、烟测清单（最短路径）

1. `/api/health` → `mysql: true`
2. 注册/登录 → 用户版顶栏切换律师版
3. AI 咨询提问 → 回答含引用或明确「未检索到」
4. 法规检索 / 类案参考各搜一条
5. 发案源 → 律师认领 → 模拟联系
6. 意见书 / 文书 / 计算器各跑一次
7. 合同审查页显示「即将开放」；`POST /api/contracts/review` 返回 501
