"""
llm/examples/test_config.py

验证：
 1. config.yaml 可以正确加载
 2. 环境变量覆盖 api_key 生效
 3. get_role_config() 路由逻辑正确
 4. provider 工厂可以正常实例化各适配器

运行：
  cd /path/to/tiptoro
  python3 -m llm.examples.test_config
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm.config import LLMConfig
from llm.providers import build_provider

print("=" * 60)
print("🔍 TipToro LLM Config 验证")
print("=" * 60)

# ── 1. 加载配置 ────────────────────────────────────────────────
cfg = LLMConfig().load()
print(f"\n✅ config.yaml 加载成功")
print(f"   已启用的 providers: {cfg.list_enabled_providers()}")

# ── 2. 模拟环境变量注入 api_key ────────────────────────────────
os.environ["DEEPSEEK_API_KEY"] = "sk-test-deepseek-key"
os.environ["GEMINI_API_KEY"] = "sk-test-gemini-key"

cfg2 = LLMConfig().load()
print(f"\n✅ 环境变量注入后，已启用的 providers: {cfg2.list_enabled_providers()}")

deepseek_cfg = cfg2.get_provider("deepseek")
assert deepseek_cfg.api_key == "sk-test-deepseek-key", "DeepSeek api_key 未从环境变量读取"
assert deepseek_cfg.enabled is True, "DeepSeek 未自动 enabled"
print(f"   deepseek.api_key = {deepseek_cfg.api_key}")
print(f"   deepseek.enabled = {deepseek_cfg.enabled}")

# ── 3. Role 路由验证 ───────────────────────────────────────────
print("\n✅ Role 路由测试：")
for role in ["cognitive_analysis", "text_cleanup", "report_writing"]:
    prov, model = cfg2.get_role_config(role)
    print(f"   role='{role}' → provider='{prov.name}', model='{model}'")

# ── 4. Provider 工厂实例化 ─────────────────────────────────────
print("\n✅ Provider 工厂实例化测试：")
for provider_name in cfg2.list_enabled_providers():
    pcfg = cfg2.get_provider(provider_name)
    provider = build_provider(pcfg)
    print(f"   {provider}")

print("\n🏁 所有验证通过！")
