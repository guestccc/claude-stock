"""AI 模型客户端 — Anthropic 格式（兼容智谱等代理）"""
from typing import AsyncGenerator

import anthropic
from server.config import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_TIMEOUT

# 初始化客户端
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    """懒加载客户端，避免启动时缺失 API Key 报错"""
    global _client
    if _client is None:
        if not AI_API_KEY:
            raise RuntimeError("AI_API_KEY 未配置，请在环境变量中设置")
        _client = anthropic.AsyncAnthropic(
            api_key=AI_API_KEY,
            base_url=AI_BASE_URL,
            timeout=AI_TIMEOUT,
        )
    return _client


async def stream_chat(
    system_prompt: str,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """流式调用 AI API（Anthropic Messages 格式），yield 每个文本片段

    Args:
        system_prompt: 系统提示词（Anthropic 格式单独传）
        messages: 消息列表 [{"role":"user","content":"..."}, ...]
        model: 模型名称，默认使用配置中的 AI_MODEL
        temperature: 温度参数

    Yields:
        每个流式文本片段
    """
    client = _get_client()
    model = model or AI_MODEL

    try:
        async with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n\n[错误] AI 服务调用失败: {str(e)}"
