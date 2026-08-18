"""配置模块：从 .env 读取本机配置。Key 绝不进入前端/代码库。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/app/core/config.py → 上移四级到 legal-rag/）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """应用配置，全部来自本机 .env。"""

    def __init__(self) -> None:
        # DeepSeek API（仅后端使用）
        self.deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.deepseek_chat_model: str = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

        # 知识库
        self.kb_source_dir: Path = Path(os.getenv("KB_SOURCE_DIR", PROJECT_ROOT / "data" / "kb"))
        self.vector_store_dir: Path = Path(os.getenv("VECTOR_STORE_DIR", PROJECT_ROOT / "data" / "vectorstore"))
        # 用户上传文档目录（与原始知识库分开管理）
        self.upload_dir: Path = PROJECT_ROOT / "data" / "uploads"

        # OCR（Phase 2）
        self.ocr_enabled: bool = os.getenv("OCR_ENABLED", "true").lower() in ("1", "true", "yes")
        self.ocr_lang: str = os.getenv("OCR_LANG", "ch")

        # 法规时效（Phase 2）
        self.effective_status_enabled: bool = os.getenv("EFFECTIVE_STATUS_ENABLED", "true").lower() in ("1", "true", "yes")

        # 检索参数
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        self.retrieve_top_k: int = int(os.getenv("RETRIEVE_TOP_K", "6"))
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))
        self.min_score: float = float(os.getenv("MIN_SCORE", "0.30"))

        # 会话
        self.session_dir: Path = PROJECT_ROOT / "data" / "sessions"
        self.max_history_rounds: int = int(os.getenv("MAX_HISTORY_ROUNDS", "6"))

    def ensure_dirs(self) -> None:
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
