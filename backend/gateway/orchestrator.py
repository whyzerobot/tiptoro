"""
gateway/orchestrator.py

核心调度器：加载 Skills，定义业务 Pipeline，按顺序执行各 Skill，
处理异步暂停点（如等待前端人工校对）和错误熔断。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from .context import TaskContext, TaskStatus
from .loader import registry

logger = logging.getLogger("tiptoro.gateway")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Step 类型
# ─────────────────────────────────────────────────────────────────────────────

class Step:
    """
    一个 Pipeline 步骤，对应一个已注册的 Skill handler。
    支持：顺序执行、条件跳过、暂停等待（await_human）。
    """

    def __init__(
        self,
        skill_name: str,
        await_human: bool = False,
        condition: Callable[[TaskContext], bool] | None = None,
    ):
        self.skill_name = skill_name
        self.await_human = await_human  # True = 执行后暂停等待前端反馈
        self.condition = condition      # None = 始终执行

    async def run(self, ctx: TaskContext) -> TaskContext:
        # 条件检查
        if self.condition and not self.condition(ctx):
            logger.info(f"[Step:{self.skill_name}] skipped (condition=False)")
            return ctx

        meta = registry.get(self.skill_name)
        if meta.handler is None:
            raise RuntimeError(
                f"Skill '{self.skill_name}' 已注册但尚未绑定 handler。"
                "请调用 registry.register_handler() 完成绑定。"
            )

        logger.info(f"[Step:{self.skill_name}] ▶ starting | task_id={ctx.task_id}")
        ctx.status = TaskStatus.RUNNING

        try:
            if asyncio.iscoroutinefunction(meta.handler):
                ctx = await meta.handler(ctx)
            else:
                ctx = await asyncio.to_thread(meta.handler, ctx)
        except Exception as e:
            ctx.add_error(self.skill_name, str(e))
            logger.error(f"[Step:{self.skill_name}] ❌ error: {e}")
            return ctx

        logger.info(f"[Step:{self.skill_name}] ✅ done")

        if self.await_human:
            ctx.status = TaskStatus.AWAITING_HUMAN
            logger.info(f"[Step:{self.skill_name}] ⏸ paused — awaiting human verification")

        return ctx


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Pipeline 编排器。

    用法示例：
        orch = Orchestrator()
        orch.add_step("vision-perception")
        orch.add_step("ingest-and-verify", await_human=True)
        orch.add_step("cognitive-analysis")
        ctx = await orch.run(ctx)
    """

    def __init__(self):
        self._steps: list[Step] = []

    def add_step(
        self,
        skill_name: str,
        await_human: bool = False,
        condition: Callable[[TaskContext], bool] | None = None,
    ) -> "Orchestrator":
        """链式添加 Step，返回 self 以支持方法链调用"""
        self._steps.append(Step(skill_name, await_human=await_human, condition=condition))
        return self

    async def run(
        self,
        ctx: TaskContext,
        resume_after: str | None = None,
    ) -> TaskContext:
        """
        顺序执行 Pipeline 中的所有 Step。
        - resume_after: 若不为 None，则跳过该 skill_name 之前（含）的所有步骤，
          用于在人工校对完成后「续跑」后半段 Pipeline。
        """
        skip = resume_after is not None
        for step in self._steps:
            if skip:
                if step.skill_name == resume_after:
                    skip = False   # 从这一步开始恢复执行（跳过此 step）
                continue

            ctx = await step.run(ctx)

            # 遇到错误立即熔断
            if ctx.status == TaskStatus.FAILED:
                logger.error(f"[Orchestrator] Pipeline halted at skill='{step.skill_name}'")
                return ctx

            # 遇到等待人工校对的暂停点立即返回
            if ctx.status == TaskStatus.AWAITING_HUMAN:
                return ctx

        if ctx.status == TaskStatus.RUNNING:
            ctx.status = TaskStatus.COMPLETED

        logger.info(f"[Orchestrator] 🏁 Pipeline completed | task_id={ctx.task_id}")
        return ctx


# ─────────────────────────────────────────────────────────────────────────────
# 标准 TipToro 处理流水线工厂
# ─────────────────────────────────────────────────────────────────────────────

def build_default_pipeline() -> Orchestrator:
    """
    构建默认的错题处理 Pipeline：
      vision-perception  → (await human) → ingest-and-verify → cognitive-analysis
    """
    orch = Orchestrator()
    orch.add_step("vision-perception", await_human=True)
    orch.add_step("ingest-and-verify")
    orch.add_step("cognitive-analysis")
    return orch


def build_report_pipeline() -> Orchestrator:
    """
    构建学情报告生成 Pipeline（单 Skill）
    """
    orch = Orchestrator()
    orch.add_step("report-generation")
    return orch
