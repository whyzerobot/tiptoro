"""
llm/providers/base.py

所有 Provider 适配器的抽象基类。
每个 Provider 实现 complete() 方法，接收统一的消息格式，返回统一的响应格式。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """OpenAI ChatCompletion 风格的消息对象，所有 Provider 统一使用此格式"""
    role: str    # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionRequest:
    """统一的 LLM 调用请求体"""
    messages: list[Message]
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.95
    json_mode: bool = False       # True 时要求模型输出纯 JSON（部分 provider 支持）
    extra: dict = field(default_factory=dict)  # provider 特有的附加参数


@dataclass
class CompletionResponse:
    """统一的 LLM 调用响应体"""
    content: str                  # 模型输出的文本
    model: str                    # 实际使用的模型名
    provider: str                 # provider 名
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Optional[dict] = None    # 原始 API 响应，供调试


class BaseProvider(ABC):
    """Provider 适配器基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """同步调用，发送 messages，返回 CompletionResponse"""
        ...

    def __repr__(self) -> str:
        return f"<Provider:{self.name}>"
