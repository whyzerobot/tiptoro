"""
gateway/loader.py

Skill 加载器：自动扫描 skills/ 目录，读取每个 SKILL.md 的 YAML frontmatter，
将所有合法 Skill 注册到内存中，供 Orchestrator 按名称快速查找。
"""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

SKILLS_ROOT = Path(__file__).parent.parent / "skills"


@dataclass
class SkillMeta:
    """从 SKILL.md frontmatter 解析出的 Skill 元信息"""
    name: str
    description: str
    skill_dir: Path
    handler: Optional[Callable] = field(default=None, repr=False)


class SkillRegistry:
    """全局 Skill 注册表，Key 为 Skill name (str)，Value 为 SkillMeta"""

    def __init__(self):
        self._registry: dict[str, SkillMeta] = {}

    def load_all(self) -> None:
        """扫描 skills/ 目录，将所有有效 Skill 注册进来"""
        self._registry.clear()
        if not SKILLS_ROOT.exists():
            raise FileNotFoundError(f"Skills 目录不存在: {SKILLS_ROOT}")

        for skill_dir in sorted(SKILLS_ROOT.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            meta = self._parse_skill_md(skill_dir, skill_md)
            if meta:
                self._registry[meta.name] = meta
                print(f"[SkillRegistry] ✅ Loaded skill: {meta.name}")

    def _parse_skill_md(self, skill_dir: Path, skill_md: Path) -> Optional[SkillMeta]:
        """解析 SKILL.md 文件的 YAML frontmatter"""
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None
        try:
            _, frontmatter, _ = content.split("---", 2)
            meta_dict = yaml.safe_load(frontmatter.strip())
            return SkillMeta(
                name=meta_dict["name"],
                description=meta_dict.get("description", ""),
                skill_dir=skill_dir,
            )
        except Exception as e:
            print(f"[SkillRegistry] ❌ Failed to parse {skill_md}: {e}")
            return None

    def register_handler(self, skill_name: str, handler: Callable) -> None:
        """为已注册的 Skill 绑定运行时 handler 函数"""
        if skill_name not in self._registry:
            raise KeyError(f"Skill '{skill_name}' 未注册，请先确认 SKILL.md 存在")
        self._registry[skill_name].handler = handler

    def get(self, skill_name: str) -> SkillMeta:
        if skill_name not in self._registry:
            raise KeyError(f"Skill '{skill_name}' 未找到")
        return self._registry[skill_name]

    def list_skills(self) -> list[str]:
        return list(self._registry.keys())


# 单例全局注册表
registry = SkillRegistry()
