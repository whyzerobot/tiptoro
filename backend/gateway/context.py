"""
gateway/context.py

任务上下文：贯穿一次完整处理流程的数据容器。
Orchestrator 将它在各个 Skill 之间依序传递，每个 Skill
读取自己需要的字段，写入自己输出的字段。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"   # 等待前端人工校对
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskContext:
    """
    一次错题处理任务的完整上下文。
    Skill 函数签名：handler(ctx: TaskContext) -> TaskContext
    """
    # ── 基础信息 ──────────────────────────────────────────
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    source: str = "web"           # web | feishu | wecom | api
    status: TaskStatus = TaskStatus.PENDING

    # ── Skill 1: vision-perception 输出 ──────────────────
    image_source: str = ""        # 原始图片 URL 或 base64
    clean_question_image_url: str = ""
    handwritten_answer_image_url: str = ""
    raw_question_text: str = ""
    raw_answer_text: str = ""
    vision_confidence: dict = field(default_factory=dict)

    # ── Skill 2: ingest-and-verify 输入（前端校对后填充）─
    verified_question_text: str = ""
    verified_answer_text: str = ""
    subject: str = ""
    grade: str = ""
    error_reason: str = ""

    # ── Skill 2: ingest-and-verify 输出 ──────────────────
    question_id: Optional[int] = None
    record_id: Optional[int] = None
    is_duplicate_question: bool = False

    # ── Skill 3: cognitive-analysis 输出 ─────────────────
    knowledge_nodes: list[str] = field(default_factory=list)
    analysis_summary: str = ""
    similar_question_keywords: list[str] = field(default_factory=list)

    # ── 通用错误链 ────────────────────────────────────────
    errors: list[dict] = field(default_factory=list)

    # ── 扩展元数据（供自定义 Skill 写入任意 KV）─────────
    meta: dict[str, Any] = field(default_factory=dict)

    def add_error(self, skill: str, message: str) -> None:
        self.errors.append({"skill": skill, "message": message})
        self.status = TaskStatus.FAILED

    def to_dict(self) -> dict:
        import dataclasses
        d = dataclasses.asdict(self)
        d["status"] = self.status.value
        return d
