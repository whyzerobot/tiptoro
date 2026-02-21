"""
gateway/examples/run_pipeline.py

演示如何将 Gateway 与 Skills 组合起来使用。
这里使用 Mock handler 替代真实的 OCR/LLM 调用，
用于快速验证 Gateway 调度逻辑是否正确。

运行方法：
  cd /path/to/tiptoro
  python -m gateway.examples.run_pipeline
"""
import asyncio
import sys
from pathlib import Path

# 让 Python 能找到项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gateway import (
    registry,
    TaskContext,
    TaskStatus,
    build_default_pipeline,
    build_report_pipeline,
)


# ─────────────────────────────────────────────────────────────────────────────
# Mock Skill Handlers（真实开发时替换为实际实现）
# ─────────────────────────────────────────────────────────────────────────────

def mock_vision_perception(ctx: TaskContext) -> TaskContext:
    """模拟：图像识别，返回 OCR 文本"""
    print(f"  [vision-perception] 处理图片: {ctx.image_source}")
    ctx.raw_question_text = r"若方程 $x^2 - 2x + m = 0$ 有两个实数根，求 $m$ 的取值范围"
    ctx.raw_answer_text = r"$m \leq 1$（学生答案，可能有误）"
    ctx.clean_question_image_url = "oss://bucket/clean/demo_q.jpg"
    ctx.handwritten_answer_image_url = "oss://bucket/answer/demo_a.jpg"
    ctx.vision_confidence = {"question_ocr": 0.92, "answer_ocr": 0.75}
    return ctx


def mock_ingest_and_verify(ctx: TaskContext) -> TaskContext:
    """模拟：人工校对完成后，将数据入库"""
    print(f"  [ingest-and-verify] 入库题目: {ctx.verified_question_text[:30]}...")
    ctx.question_id = 10001
    ctx.record_id = 50001
    ctx.is_duplicate_question = False
    return ctx


def mock_cognitive_analysis(ctx: TaskContext) -> TaskContext:
    """模拟：LLM 知识点归纳"""
    print(f"  [cognitive-analysis] 分析 record_id={ctx.record_id}")
    ctx.knowledge_nodes = ["一元二次方程", "根的判别式", "参数范围求解"]
    ctx.analysis_summary = (
        "学生在计算 Delta = b^2-4ac 时未考虑 m 的范围需要使 Delta>=0，"
        "直接给出了错误答案。需要强化判别式法求参数范围这一考点。"
    )
    ctx.similar_question_keywords = ["一元二次方程实数根", "判别式求参数范围"]
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    # 1. 加载所有 Skills (扫描 SKILL.md)
    registry.load_all()
    print(f"\n已注册 Skills: {registry.list_skills()}\n")

    # 2. 绑定 Mock Handler 到各 Skill
    registry.register_handler("vision-perception", mock_vision_perception)
    registry.register_handler("ingest-and-verify", mock_ingest_and_verify)
    registry.register_handler("cognitive-analysis", mock_cognitive_analysis)

    # 3. 构建默认 Pipeline
    pipeline = build_default_pipeline()

    # ── 阶段 1：图像识别（执行后暂停等待人工校对）────────────────────────
    ctx = TaskContext(user_id="student_001", image_source="oss://bucket/raw/q1.jpg")
    print("=" * 60)
    print(f"🚀 Pipeline 启动 | task_id={ctx.task_id}")
    print("=" * 60)

    ctx = await pipeline.run(ctx)

    assert ctx.status == TaskStatus.AWAITING_HUMAN, f"预期 AWAITING_HUMAN，实际 {ctx.status}"
    print(f"\n⏸  已暂停 | 等待前端人工校对...")
    print(f"   识别到题干: {ctx.raw_question_text[:40]}...")
    print(f"   识别到错答: {ctx.raw_answer_text}")

    # ── 模拟前端用户完成校对并填入数据 ───────────────────────────────────
    ctx.verified_question_text = ctx.raw_question_text   # 用户无修改，直接确认
    ctx.verified_answer_text = r"$m \leq 1$"             # 用户确认了错答
    ctx.subject = "math"
    ctx.grade = "high_1"
    ctx.error_reason = "concept_unclear"

    # ── 阶段 2：续跑 Pipeline（从 ingest-and-verify 开始）────────────────
    print("\n▶  人工校对完成，续跑 Pipeline...")
    ctx = await pipeline.run(ctx, resume_after="vision-perception")

    assert ctx.status == TaskStatus.COMPLETED, f"预期 COMPLETED，实际 {ctx.status}"
    print("\n" + "=" * 60)
    print("🏁 Pipeline 完成！")
    print("=" * 60)
    print(f"  question_id   : {ctx.question_id}")
    print(f"  record_id     : {ctx.record_id}")
    print(f"  knowledge_nodes: {ctx.knowledge_nodes}")
    print(f"  analysis_summary: {ctx.analysis_summary[:60]}...")
    print(f"  similar_keywords: {ctx.similar_question_keywords}")


if __name__ == "__main__":
    asyncio.run(main())
