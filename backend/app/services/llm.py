"""DeepSeek LLM 客户端（仅后端使用，Key 从 .env 读取）。"""
from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


def get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )


def chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1200,
    timeout: float = 90.0,
) -> str:
    """调用 DeepSeek chat 模型，返回回复文本。"""
    if not settings.deepseek_api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在项目 .env 文件中填写。")
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.deepseek_chat_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return (resp.choices[0].message.content or "").strip()
