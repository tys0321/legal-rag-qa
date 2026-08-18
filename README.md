# 法律知识问答助手（RAG Legal Q&A Assistant）

基于 RAG 的法律知识问答 Web 应用。用户提问 → 检索法律知识库 → LLM 生成带引用溯源的回答。
**成熟前后端架构**：FastAPI 分层后端 + Vite/React/TypeScript 工程化前端。

## 功能

- 🔐 **用户系统**：注册/登录/登出，密码哈希存储（PBKDF2），Bearer Token 鉴权，会话按用户隔离
  - **注册约束**：用户名不可为空（≥2 字符）；密码至少 6 位且**必须同时包含字母和数字**（前后端双重校验）
  - **管理员账号**：初始管理员由 `scripts/init_admin.py` 创建，密码通过 `scripts/reset_admin_password.py` 设置（从环境变量 `ADMIN_PASSWORD` 或交互输入读取，不写入代码）。**部署后请立即修改默认密码并妥善保管。**
- 🛡️ **角色分区**：普通用户仅使用问答助手；admin 可进入「管理后台」（用户列表搜索/角色管理/删除用户、操作日志、系统统计、模型与 OCR 状态、版本管理），非 admin 访问 API 返回 403
- 📜 **操作日志**：删除用户、修改角色、创建/恢复/删除快照等管理操作全程留痕（谁、何时、做了什么）
- 🕐 **版本管理（零 git 基础）**：像游戏存档一样创建/恢复系统快照（用户+会话+知识库索引 zip 打包），管理后台一键创建/列表/恢复/删除，恢复后无需重启进程
- 🧑‍⚖️ **律师视角回答**：涉及时效/管辖的维权场景，突出诉讼时效期间与起算点、管辖法院一般规则、证据固定第一步、专业律师求助建议
- ⚡ **快慢分流**：常识问题直接回答（fast）；法条/具体规定走完整 RAG（slow）；拿不准一律走 slow
- 📚 **引用溯源**：回答标注 [1][2] 引用，可展开查看原文出处；含「第X条」时条款号精确匹配（感知法律名，消解同名条款歧义）
- 💬 **多轮对话 + 会话历史**：左侧边栏展示会话列表（自动标题、时间），点击切换历史会话、新建/删除会话；**每个用户的对话历史完全独立**（前端按用户强制重挂载，杜绝串号残留）
- 📝 **回答风格**：DeepSeek 式自然专业表达——直接切入结论、按情况自然分层（加粗小节）、步骤用简洁列表、语言流畅平实；法条统一《××法》第×条格式并自动高亮
  - **独立分行排版**：每条编号/要点单独成行，标题与说明分行，小节间留空行；前端块级渲染（编号徽标 + 小节标题 + 保留换行），回答结构一目了然
- 📄 **文档管理（侧边栏）**：上传 docx/pdf/txt/md（异步后台入库）、文档列表（含时效状态）、删除；中文文件名自动修复
- 🔍 **扫描件 OCR**：图片型 PDF 自动用 RapidOCR 识别文字（免费离线）
- ⏱️ **法规时效提示**：自动检测法规效力状态（现行有效/已修订/已废止/部分失效），回答中提示"该法已被修订"
- 📎 **相似案例推荐**：回答下方附带司法解释/案例类相关文档推荐
- ⚠️ **免责提示**：AI 生成内容仅供参考，不构成法律意见

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vite 6 + React 18 + TypeScript（组件化、类型安全、API 客户端） |
| 后端 | FastAPI + 分层架构（api / services / repositories / schemas / core） |
| LLM | DeepSeek API（云端，Key 仅存后端 .env） |
| 嵌入 | fastembed + BAAI/bge-small-zh-v1.5（本地离线，免费，512 维） |
| 向量库 | 自研轻量 numpy 余弦索引（Phase 3 换 Milvus/Qdrant，接口不变） |
| 测试 | pytest（56 个用例）+ 统一错误处理 + 结构化日志 |
| OCR | RapidOCR（onnxruntime，免费离线，中文扫描件自动识别） |
| 时效 | 规则引擎检测效力状态（现行有效/已修订/已废止/部分失效） |
| 用户 | SQLite + PBKDF2 密码哈希 + Bearer Token 鉴权 |
| 版本 | 快照 zip 打包（app.db + 向量库 + 上传文档），零 git 可视化恢复 |

## 目录结构

```
legal-rag/
├── backend/
│   ├── app/
│   │   ├── main.py            # 应用入口：路由组装、异常处理、前端托管
│   │   ├── api/               # 路由层（chat / documents）
│   │   ├── services/          # 业务层（rag / router / ingest / chunker / embeddings / llm）
│   │   ├── repositories/      # 数据层（vector_store / sessions）
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   └── core/              # 配置 / 日志 / 异常
│   └── tests/                 # pytest 测试
├── frontend/
│   ├── src/
│   │   ├── api/               # API 客户端 + 类型定义
│   │   ├── components/        # MessageBubble / InputBar 等组件
│   │   ├── hooks/             # useChat 状态管理
│   │   └── styles/
│   └── dist/                  # 构建产物（由后端托管）
├── data/                      # 向量库 / 模型缓存 / 会话（gitignore）
└── 需求确认书.md
```

## 快速开始

### 1. 配置

```powershell
Copy-Item .env.example .env
# 编辑 .env 填写 DEEPSEEK_API_KEY 与 KB_SOURCE_DIR
```

### 2. 后端

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. 入库（示例：法律类别）

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -X utf8 -c "from app.core.config import settings; from app.services.ingest import ingest_documents; settings.ensure_dirs(); print(ingest_documents(settings.kb_source_dir, category='法律'))"
```

### 4. 前端（开发 / 构建）

```powershell
cd frontend
pnpm install
pnpm run dev        # 开发服务器 http://localhost:5173（代理 /api）
pnpm run build      # 构建到 dist/，由后端 8000 端口托管
```

浏览器打开 http://127.0.0.1:8000

## API 文档

启动后访问 http://127.0.0.1:8000/docs（Swagger 自动生成）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/register | 注册 `{username, password}` |
| POST | /api/auth/login | 登录，返回 token |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 当前用户 |
| POST | /api/chat | 对话 `{message, session_id?}`（需 Bearer token） |
| GET | /api/sessions | 会话列表 |
| GET | /api/sessions/{id}/messages | 会话历史 |
| POST | /api/sessions/{id}/rename | 会话改名 |
| DELETE | /api/sessions/{id} | 删除会话 |
| GET | /api/stats | 知识库统计 |
| GET | /api/documents | 文档列表（含效力状态） |
| POST | /api/upload | 上传文档（multipart，异步后台入库） |
| POST | /api/delete | 删除文档 `{doc_id}` |
| POST | /api/sessions/batch-delete | 批量删除会话 `{session_ids}` |
| POST | /api/admin/backup/create | 创建版本快照（admin） |
| GET | /api/admin/backup/list | 快照列表（admin） |
| POST | /api/admin/backup/{name}/restore | 恢复快照（admin，无需重启） |
| DELETE | /api/admin/backup/{name} | 删除快照（admin） |

## 安全说明

- **API Key 只存在于后端 .env，绝不进入前端/代码库**（见 .gitignore）
- **用户密码**：PBKDF2 哈希存储（100k 轮），不存明文；Token 随机 64 hex，存服务端
- 浏览器只与后端通信，由后端代发 DeepSeek 请求，Token 不外泄
- 发布部署：服务端代发（默认）/ BYOK（用户自带 Key）/ 混合模式

## 路线图

- [x] Phase 1：MVP 核心链路 + 成熟前后端架构
- [x] Phase 2：扫描件 OCR、文档上传管理、法规时效、相似案例推荐
- [x] Phase 3a：产品化改造（用户系统、会话历史、侧边栏、全新视觉）
- [ ] Phase 3b：万份级向量库（Milvus/Qdrant）、网页法规采集、企业权限与部署
