"""
config/loader.py

统一配置加载器 (AppSettings)。
- 读取 config/settings.yaml（行为配置，提交到 git）
- 自动加载 .env 文件（密钥，不提交 git）
- 环境变量优先级高于 yaml 中的任何值
- 提供全局单例 app_settings

所有模块（llm/、infra/）改为从此处读取配置，
不再各自维护独立的 yaml 文件和加载器。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

SETTINGS_PATH = Path(__file__).parent / "settings.yaml"
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def _load_dotenv() -> None:
    """简单的 .env 加载器，无需 python-dotenv 依赖。
    若已安装 python-dotenv 则优先使用，否则自行解析。"""
    if not ENV_FILE.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE, override=False)  # 已有的环境变量不覆盖
        return
    except ImportError:
        pass
    # 降级：手动解析
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


# ── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class DatabaseConfig:
    driver: Literal["sqlite", "postgresql"]
    path: str = "./data/tiptoro_local.db"
    host: str = "localhost"
    port: int = 5432
    name: str = "tiptoro"
    user: str = ""
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10
    echo_sql: bool = False

    @property
    def url(self) -> str:
        if self.driver == "sqlite":
            p = (PROJECT_ROOT / self.path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{p}"
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass
class StorageConfig:
    driver: Literal["local", "aliyun_oss", "aws_s3"]
    base_url: str = ""
    root_dir: str = "./data/storage"
    bucket: str = ""
    region: str = ""
    endpoint: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    secret_access_key: str = ""


@dataclass
class ProviderSettings:
    name: str
    base_url: str
    default_model: str
    timeout: int = 60
    max_retries: int = 3
    # 密钥从环境变量注入，不存 yaml
    api_key: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@dataclass
class LLMRoleSettings:
    role: str
    provider: str
    model: str


@dataclass
class GenerationDefaults:
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.95


@dataclass
class LLMSettings:
    roles: dict[str, LLMRoleSettings] = field(default_factory=dict)
    providers: dict[str, ProviderSettings] = field(default_factory=dict)
    generation_defaults: GenerationDefaults = field(default_factory=GenerationDefaults)


# ── 主加载器 ──────────────────────────────────────────────────────────────────

class AppSettings:
    """全局统一配置，整个应用的唯一配置入口。"""

    def __init__(self):
        self._db: DatabaseConfig | None = None
        self._storage: StorageConfig | None = None
        self._llm: LLMSettings | None = None
        self._active_env: str = "local"
        self._loaded = False

    def load(self, settings_path: Path = SETTINGS_PATH) -> "AppSettings":
        _load_dotenv()

        with open(settings_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._active_env = os.environ.get("TIPTORO_ENV", raw.get("active_env", "local"))
        if self._active_env not in ("local", "cloud"):
            raise ValueError(f"TIPTORO_ENV must be 'local' or 'cloud', got '{self._active_env}'")

        self._db = self._parse_db(raw.get("database", {}))
        self._storage = self._parse_storage(raw.get("storage", {}))
        self._llm = self._parse_llm(raw.get("llm", {}))
        self._loaded = True
        return self

    # ── DB ────────────────────────────────────────────────────────────────────

    def _parse_db(self, cfg: dict) -> DatabaseConfig:
        env_cfg = cfg.get(self._active_env, {})
        driver = env_cfg.get("driver", "sqlite")
        if driver == "sqlite":
            return DatabaseConfig(
                driver="sqlite",
                path=env_cfg.get("path", "./data/tiptoro_local.db"),
                echo_sql=env_cfg.get("echo_sql", True),
            )
        return DatabaseConfig(
            driver="postgresql",
            host=os.environ.get("DB_HOST", env_cfg.get("host", "localhost")),
            port=int(os.environ.get("DB_PORT", env_cfg.get("port", 5432))),
            name=os.environ.get("DB_NAME", env_cfg.get("name", "tiptoro")),
            user=os.environ.get("DB_USER", env_cfg.get("user", "")),
            password=os.environ.get("DB_PASSWORD", env_cfg.get("password", "")),
            pool_size=env_cfg.get("pool_size", 10),
            max_overflow=env_cfg.get("max_overflow", 20),
            echo_sql=env_cfg.get("echo_sql", False),
        )

    # ── Storage ───────────────────────────────────────────────────────────────

    def _parse_storage(self, cfg: dict) -> StorageConfig:
        env_cfg = cfg.get(self._active_env, {})
        driver = env_cfg.get("driver", "local")
        if driver == "local":
            return StorageConfig(
                driver="local",
                root_dir=env_cfg.get("root_dir", "./data/storage"),
                base_url=env_cfg.get("base_url", ""),
            )
        if driver == "aliyun_oss":
            return StorageConfig(
                driver="aliyun_oss",
                bucket=env_cfg.get("bucket", ""),
                region=env_cfg.get("region", ""),
                endpoint=env_cfg.get("endpoint", ""),
                base_url=env_cfg.get("base_url", ""),
                access_key_id=os.environ.get("OSS_ACCESS_KEY_ID", ""),
                access_key_secret=os.environ.get("OSS_ACCESS_KEY_SECRET", ""),
            )
        if driver == "aws_s3":
            return StorageConfig(
                driver="aws_s3",
                bucket=env_cfg.get("bucket", ""),
                region=env_cfg.get("region", ""),
                base_url=env_cfg.get("base_url", ""),
                access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
                secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            )
        raise ValueError(f"Unknown storage driver: {driver}")

    # ── LLM ───────────────────────────────────────────────────────────────────

    def _parse_llm(self, cfg: dict) -> LLMSettings:
        roles = {
            role_name: LLMRoleSettings(
                role=role_name,
                provider=rcfg["provider"],
                model=rcfg.get("model", ""),
            )
            for role_name, rcfg in (cfg.get("roles") or {}).items()
        }

        # API key 环境变量名约定: {PROVIDER_NAME}_API_KEY
        providers: dict[str, ProviderSettings] = {}
        for name, pcfg in (cfg.get("providers") or {}).items():
            api_key = os.environ.get(f"{name.upper()}_API_KEY", "")
            extra = {}
            if name == "minimax":
                extra["group_id"] = os.environ.get("MINIMAX_GROUP_ID", "")
            providers[name] = ProviderSettings(
                name=name,
                base_url=pcfg.get("base_url", ""),
                default_model=pcfg.get("default_model", ""),
                timeout=pcfg.get("timeout", 60),
                max_retries=pcfg.get("max_retries", 3),
                api_key=api_key,
                extra=extra,
            )

        gd = cfg.get("generation_defaults") or {}
        defaults = GenerationDefaults(
            temperature=gd.get("temperature", 0.2),
            max_tokens=gd.get("max_tokens", 2048),
            top_p=gd.get("top_p", 0.95),
        )
        return LLMSettings(roles=roles, providers=providers, generation_defaults=defaults)

    # ── 公共查询 API ──────────────────────────────────────────────────────────

    @property
    def active_env(self) -> str:
        self._ensure_loaded()
        return self._active_env

    def get_db(self) -> DatabaseConfig:
        self._ensure_loaded()
        return self._db  # type: ignore

    def get_storage(self) -> StorageConfig:
        self._ensure_loaded()
        return self._storage  # type: ignore

    def get_llm(self) -> LLMSettings:
        self._ensure_loaded()
        return self._llm  # type: ignore

    def get_llm_role(self, role: str) -> tuple[ProviderSettings, str]:
        """返回 (ProviderSettings, model_name)，含自动 fallback 逻辑"""
        self._ensure_loaded()
        llm = self._llm  # type: ignore
        role_cfg = llm.roles.get(role)
        if not role_cfg:
            raise KeyError(f"LLM role '{role}' not found in settings.yaml")

        provider = llm.providers.get(role_cfg.provider)
        if not provider or not provider.enabled:
            fallback = llm.roles.get("fallback")
            if not fallback:
                raise RuntimeError(
                    f"Provider '{role_cfg.provider}' has no API key and no fallback defined."
                )
            provider = llm.providers[fallback.provider]
            model = fallback.model or provider.default_model
            print(f"[AppSettings] ⚠ role='{role}' fallback → {provider.name}/{model}")
        else:
            model = role_cfg.model or provider.default_model

        return provider, model

    def list_enabled_providers(self) -> list[str]:
        self._ensure_loaded()
        return [n for n, p in (self._llm.providers if self._llm else {}).items() if p.enabled]

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()


# 全局单例
app_settings = AppSettings()
