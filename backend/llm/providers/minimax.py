"""
llm/providers/minimax.py

MiniMax 适配器。MiniMax 使用自己的 ChatCompletion Pro 接口，
鉴权需要同时提供 api_key (Bearer Token) 和 group_id (URL 参数)。
"""
from __future__ import annotations

import time

import requests

from .base import BaseProvider, CompletionRequest, CompletionResponse
from ..config import ProviderConfig


class MiniMaxProvider(BaseProvider):

    def __init__(self, cfg: ProviderConfig):
        super().__init__("minimax")
        self.cfg = cfg
        self.group_id = cfg.extra.get("group_id", "")

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.group_id:
            raise ValueError("[MiniMax] group_id 未配置，请在 config.yaml 或环境变量 MINIMAX_GROUP_ID 中设置。")

        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": request.model,
            "messages": [{"sender_type": self._role_map(m.role), "text": m.content}
                         for m in request.messages if m.role != "system"],
            "temperature": request.temperature,
            "tokens_to_generate": request.max_tokens,
            "top_p": request.top_p,
        }
        # MiniMax 用 bot_setting 传 system prompt
        system_msgs = [m.content for m in request.messages if m.role == "system"]
        if system_msgs:
            payload["bot_setting"] = [{"bot_name": "TipToro", "content": system_msgs[0]}]
        payload.update(request.extra)

        url = f"{self.cfg.base_url}/text/chatcompletion_v2?GroupId={self.group_id}"

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.cfg.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["messages"][0]["text"]
                usage = data.get("usage", {})
                return CompletionResponse(
                    content=content,
                    model=request.model,
                    provider="minimax",
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    raw=data,
                )
            except Exception as e:
                if attempt == self.cfg.max_retries:
                    raise RuntimeError(f"[MiniMax] 调用失败（重试 {attempt} 次）: {e}") from e
                time.sleep(2 ** attempt)

    @staticmethod
    def _role_map(role: str) -> str:
        return {"user": "USER", "assistant": "BOT"}.get(role, "USER")
