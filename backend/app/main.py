"""FastAPI 应用入口：组装路由、统一异常处理、托管前端构建产物。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin_api import router as admin_router
from app.api.auth_api import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.sessions_api import router as sessions_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.repositories import database as db

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
setup_logging(log_dir=PROJECT_ROOT / "data" / "logs")
logger = logging.getLogger("app")

settings.ensure_dirs()
db.init_db()

app = FastAPI(
    title="法律知识问答助手 API",
    description="基于 RAG 的法律知识问答系统：快慢分流、引用溯源、多轮对话。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(sessions_router)
app.include_router(admin_router)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content={"error": "服务器内部错误"})


# ---------- 前端托管（Vite 构建产物） ----------
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIST / "index.html")


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
