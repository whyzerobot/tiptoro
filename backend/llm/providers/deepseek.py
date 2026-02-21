"""
llm/providers/deepseek.py

DeepSeek 适配器。DeepSeek 兼容 OpenAI ChatCompletion 接口，
使用 requests 直接调用 HTTP 接口（无需官方 SDK）。
"""
from __future__ import annotations

import json
import time

import requests

from .base import BaseProvider, CompletionRequest, CompletionResponse
from ..config import ProviderConfig


class DeepSeekProvider(BaseProvider):

    def __init__(self, cfg: ProviderConfig):
        super().__init__("deepseek")
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
                choice = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return CompletionResponse(
                    content=choice,
                    model=data.get("model", request.model),
                    provider="deepseek",
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    raw=data,
                )
            except Exception as e:
                if attempt == self.cfg.max_retries:
                    raise RuntimeError(f"[DeepSeek] 调用失败（重试 {attempt} 次）: {e}") from e
                time.sleep(2 ** attempt)
