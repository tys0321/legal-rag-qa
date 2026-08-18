"""统一异常处理与 API 错误模型。"""
from __future__ import annotations


class AppError(Exception):
    """应用层业务异常，message 会直接暴露给前端。"""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, 404)


class ConfigError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 500)


class LLMError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 502)
