"""
llm/providers/openai_compat.py

OpenAI 兼容适配器（通用版）。
DeepSeek、OpenAI、Grok (xAI) 均兼容 OpenAI ChatCompletion API，
共用此适配器，仅 base_url 和 provider name 不同。
"""
from __future__ import annotations

import time

import requests

from .base import BaseProvider, CompletionRequest, CompletionResponse
from ..config import ProviderConfig


class OpenAICompatProvider(BaseProvider):
    """通用 OpenAI 兼容适配器，OpenAI / Grok 共用此类"""

    def __init__(self, cfg: ProviderConfig, provider_name: str):
        super().__init__(provider_name)
        self.cfg = cfg

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        payload.update(request.extra)

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.cfg.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.cfg.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return CompletionResponse(
                    content=content,
                    model=data.get("model", request.model),
                    provider=self.name,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    raw=data,
                )
            except Exception as e:
                if attempt == self.cfg.max_retries:
                    raise RuntimeError(
                        f"[{self.name}] 调用失败（重试 {attempt} 次）: {e}"
                    ) from e
                time.sleep(2 ** attempt)
