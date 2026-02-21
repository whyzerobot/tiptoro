"""
gateway/__init__.py

对外暴露的公共接口：只需导入此包即可使用 Gateway。
"""
from .loader import registry, SkillRegistry, SkillMeta
from .context import TaskContext, TaskStatus
from .orchestrator import Orchestrator, build_default_pipeline, build_report_pipeline

__all__ = [
    "registry",
    "SkillRegistry",
    "SkillMeta",
    "TaskContext",
    "TaskStatus",
    "Orchestrator",
    "build_default_pipeline",
    "build_report_pipeline",
]
