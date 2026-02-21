"""
users/context.py

AI 上下文构建器。
在调用 LLM（llm_call）前，将用户的 soul.md + user.md 内容
注入到 System Prompt 中，让 AI 针对该学生的特性给出更好的反馈。

使用示例：
    from users.context import build_user_context
    from llm import llm_call, Message

    system_prefix = build_user_context(user_id=123)
    response = llm_call(
        role="cognitive_analysis",
        messages=[
            Message(role="system", content=system_prefix + "\\n\\n" + base_system_prompt),
            Message(role="user", content=question_text),
        ],
    )
"""
from __future__ import annotations

from users.space import read_soul, read_user_profile_md

_CONTEXT_TEMPLATE = """\
## 当前用户上下文

以下是关于你正在服务的学生的背景信息，请在回答时参考这些信息：

### AI 行为定义 (soul.md)
{soul}

### 学生自我介绍 (user.md)
{user_profile}

---
请始终根据以上背景信息调整你的回答风格和内容。
"""


def build_user_context(user_id: int) -> str:
    """
    为指定用户构建 LLM System Prompt 前缀。
    自动读取 soul.md + user.md，拼装为结构化上下文字符串。

    Args:
        user_id: 用户 ID

    Returns:
        str: 格式化的上下文字符串，可直接拼接到 System Prompt 前
    """
    soul = read_soul(user_id)
    user_profile = read_user_profile_md(user_id)
    return _CONTEXT_TEMPLATE.format(soul=soul.strip(), user_profile=user_profile.strip())


def inject_user_context(
    user_id: int,
    base_system_prompt: str,
) -> str:
    """
    将用户上下文注入到已有 System Prompt 的前缀。

    Args:
        user_id: 用户 ID
        base_system_prompt: Skill 原有的系统提示词

    Returns:
        str: 合并后的 System Prompt（用户上下文 + Skill 系统提示）
    """
    context = build_user_context(user_id)
    return context + "\n\n" + base_system_prompt
