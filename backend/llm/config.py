"""
llm/config.py

LLM 配置模块 — 现在是 config.AppSettings 的薄包装。
保留原有接口（ProviderConfig, LLMConfig, llm_config）以确保向后兼容，
内部全部委托给统一配置加载器 config.loader.app_settings。
"""
from __future__ import annotations

from config.loader import app_settings, ProviderSettings as ProviderConfig, GenerationDefaults


class LLMConfig:
    """向后兼容的 LLM 配置访问器，委托给 app_settings"""

    def get_role_config(self, role: str) -> tuple[ProviderConfig, str]:
        """返回 (ProviderConfig, model_name)，含 fallback 逻辑"""
        return app_settings.get_llm_role(role)

    def get_provider(self, name: str) -> ProviderConfig:
        llm = app_settings.get_llm()
        if name not in llm.providers:
            raise KeyError(f"Provider '{name}' not found in settings.yaml")
        return llm.providers[name]

    def get_defaults(self) -> GenerationDefaults:
        return app_settings.get_llm().generation_defaults

    def list_enabled_providers(self) -> list[str]:
        return app_settings.list_enabled_providers()


# 保留全局单例名称，供老代码直接使用
llm_config = LLMConfig()
