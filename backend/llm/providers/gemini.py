"""
llm/providers/gemini.py

Google Gemini 适配器。通过 REST API 调用 generateContent 接口。
将统一的 messages 格式映射到 Gemini 的 contents 结构。
"""
from __future__ import annotations

import json
import time

import requests

from .base import BaseProvider, CompletionRequest, CompletionResponse
from ..config import ProviderConfig


class GeminiProvider(BaseProvider):

    def __init__(self, cfg: ProviderConfig):
        super().__init__("gemini")
        self.cfg = cfg

    def _build_contents(self, messages: list) -> tuple[str | None, list]:
        """将 ChatCompletion messages 转为 Gemini contents 格式，system 单独提取"""
        system_instruction = None
        contents = []
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
        return system_instruction, contents

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        system_instruction, contents = self._build_contents(request.messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
                "topP": request.top_p,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if request.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        url = (
            f"{self.cfg.base_url}/models/{request.model}:generateContent"
            f"?key={self.cfg.api_key}"
        )

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.cfg.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                return CompletionResponse(
                    content=content,
                    model=request.model,
                    provider="gemini",
                    input_tokens=usage.get("promptTokenCount", 0),
                    output_tokens=usage.get("candidatesTokenCount", 0),
                    raw=data,
                )
            except Exception as e:
                if attempt == self.cfg.max_retries:
                    raise RuntimeError(f"[Gemini] 调用失败（重试 {attempt} 次）: {e}") from e
                time.sleep(2 ** attempt)
