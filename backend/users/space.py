"""
users/space.py

用户个人空间管理器。
每个用户拥有两个核心 Markdown 文件：
  - soul.md  : AI 属性定义（告诉 AI 如何对待这个用户）
  - user.md  : 用户自我描述（学科特长、学习风格、性格等）

存储路径（通过 get_storage() 读写，本地/云端自动切换）：
  user_spaces/{user_id}/soul.md
  user_spaces/{user_id}/user.md
"""
from __future__ import annotations

from infra.storage import get_storage

# ── 默认模版 ──────────────────────────────────────────────────

_DEFAULT_SOUL_MD = """\
# Soul Configuration

你是 TipToro 的专属学习助手。
请用鼓励、耐心、简洁的语气与学生互动。
优先帮助学生理解错误的根因，而不是直接给出答案。
在分析知识点时，结合学生的薄弱环节给出针对性建议。
"""

_DEFAULT_USER_MD = """\
# 用户简介

> 请根据实际情况填写以下内容，帮助 AI 更好地了解你。

- **姓名**：（未填写）
- **年级**：（未填写，例如：高中一年级）
- **擅长学科**：（未填写，例如：语文、英语）
- **薄弱学科**：（未填写，例如：数学几何部分）
- **学习风格**：（未填写，例如：视觉型，喜欢图表和例题）
- **自我评价**：（未填写，例如：认真但容易紧张，需要多鼓励）
"""


def _key(user_id: int, filename: str) -> str:
    """构建存储 key"""
    return f"user_spaces/{user_id}/{filename}"


def read_soul(user_id: int) -> str:
    """读取 soul.md，若不存在则返回默认模版"""
    storage = get_storage()
    key = _key(user_id, "soul.md")
    if not storage.exists(key):
        return _DEFAULT_SOUL_MD
    return storage.get(key).decode("utf-8")


def write_soul(user_id: int, content: str) -> str:
    """保存 soul.md，返回访问 URL"""
    storage = get_storage()
    return storage.put(_key(user_id, "soul.md"), content.encode("utf-8"), content_type="text/markdown")


def read_user_profile_md(user_id: int) -> str:
    """读取 user.md，若不存在则返回默认模版"""
    storage = get_storage()
    key = _key(user_id, "user.md")
    if not storage.exists(key):
        return _DEFAULT_USER_MD
    return storage.get(key).decode("utf-8")


def write_user_profile_md(user_id: int, content: str) -> str:
    """保存 user.md，返回访问 URL"""
    storage = get_storage()
    return storage.put(_key(user_id, "user.md"), content.encode("utf-8"), content_type="text/markdown")


def init_user_space(user_id: int) -> None:
    """
    首次注册后调用：用默认模版初始化用户空间。
    若文件已存在则跳过（幂等）。
    """
    storage = get_storage()
    for filename, default in [
        ("soul.md", _DEFAULT_SOUL_MD),
        ("user.md", _DEFAULT_USER_MD),
    ]:
        key = _key(user_id, filename)
        if not storage.exists(key):
            storage.put(key, default.encode("utf-8"), content_type="text/markdown")
    print(f"[UserSpace] ✅ user_id={user_id} 空间初始化完成")


def list_space_files(user_id: int) -> list[str]:
    """列出用户空间已有文件（本地模式）"""
    # 本地模式：直接扫描目录
    from pathlib import Path
    from config.loader import app_settings
    st = app_settings.get_storage()
    if st.driver == "local":
        root = Path(st.root_dir) / "user_spaces" / str(user_id)
        if root.exists():
            return [f.name for f in root.iterdir() if f.is_file()]
    return []
