"""
llm/providers/__init__.py

Provider 工厂函数：根据 ProviderConfig 自动实例化正确的适配器类。
"""
from ..config import ProviderConfig
from .base import BaseProvider, Message, CompletionRequest, CompletionResponse
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider
from .minimax import MiniMaxProvider


def build_provider(cfg: ProviderConfig) -> BaseProvider:
    """根据 provider name 工厂化对应的适配器实例"""
    name = cfg.name
    if name == "deepseek":
        return DeepSeekProvider(cfg)
    elif name == "gemini":
        return GeminiProvider(cfg)
    elif name in ("openai", "grok"):
        return OpenAICompatProvider(cfg, provider_name=name)
    elif name == "minimax":
        return MiniMaxProvider(cfg)
    else:
        raise ValueError(f"[ProviderFactory] 未知的 provider: '{name}'")


__all__ = [
    "build_provider",
    "BaseProvider",
    "Message",
    "CompletionRequest",
    "CompletionResponse",
]
