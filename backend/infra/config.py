"""
infra/config.py

Infra 配置模块 — 现在是 config.AppSettings 的薄包装。
保留原有接口（DatabaseConfig, StorageConfig, InfraConfig, infra_config）以确保向后兼容，
内部全部委托给统一配置加载器 config.loader.app_settings。
"""
from __future__ import annotations

from config.loader import app_settings, DatabaseConfig, StorageConfig


class InfraConfig:
    """向后兼容的 Infra 配置访问器，委托给 app_settings"""

    def load(self) -> "InfraConfig":
        app_settings._ensure_loaded()
        return self

    def get_db_config(self) -> DatabaseConfig:
        return app_settings.get_db()

    def get_storage_config(self) -> StorageConfig:
        return app_settings.get_storage()

    @property
    def active_env(self) -> str:
        return app_settings.active_env


# 保留全局单例名称，供老代码直接使用
infra_config = InfraConfig()
