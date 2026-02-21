"""
llm/client.py

统一 LLM 客户端入口（Skills 唯一调用方式）。

使用方法（在 Skill handler 或 script 中）：

    from llm import llm_call, Message

    response = llm_call(
        role="cognitive_analysis",       # 从 config.yaml roles 中路由
        messages=[
            Message(role="system", content="你是一位中学数学老师..."),
            Message(role="user", content="题目: ...  错答: ..."),
        ],
        json_mode=True,
    )
    print(response.content)              # str 格式的模型输出
"""
from __future__ import annotations

from typing import Optional

from .config import llm_config, ProviderConfig
from .providers import build_provider, Message, CompletionRequest, CompletionResponse

# Provider 实例缓存：避免每次调用都重新构建 HTTP Session
_provider_cache: dict[str, object] = {}


def _get_provider(cfg: ProviderConfig):
    """获取或创建 provider 实例（懒加载 + 缓存）"""
    if cfg.name not in _provider_cache:
        _provider_cache[cfg.name] = build_provider(cfg)
    return _provider_cache[cfg.name]


def llm_call(
    role: str,
    messages: list[Message],
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    json_mode: bool = False,
    extra: Optional[dict] = None,
) -> CompletionResponse:
    """
    统一 LLM 调用入口。

    Args:
        role:        功能角色名称，对应 config.yaml 中 roles 的 key
                     (如 "cognitive_analysis", "text_cleanup", "report_writing")
        messages:    对话消息列表 [Message(role=..., content=...), ...]
        temperature: 覆盖 config 默认值（可选）
        max_tokens:  覆盖 config 默认值（可选）
        top_p:       覆盖 config 默认值（可选）
        json_mode:   True 时请求模型返回纯 JSON 字符串
        extra:       传递给 provider 的额外参数字典

    Returns:
        CompletionResponse  (content, model, provider, token counts, raw)
    """
    # 1. 从 config 获取目标 provider 和 model（含 fallback 逻辑）
    provider_cfg, model = llm_config.get_role_config(role)

    # 2. 取默认生成参数
    defaults = llm_config.get_defaults()

    # 3. 构建请求对象
    request = CompletionRequest(
        messages=messages,
        model=model,
        temperature=temperature if temperature is not None else defaults.temperature,
        max_tokens=max_tokens if max_tokens is not None else defaults.max_tokens,
        top_p=top_p if top_p is not None else defaults.top_p,
        json_mode=json_mode,
        extra=extra or {},
    )

    # 4. 获取 provider 适配器并调用
    provider = _get_provider(provider_cfg)
    return provider.complete(request)
