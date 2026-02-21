"""
infra/models.py

SQLAlchemy ORM 数据模型定义。
所有表在 local (SQLite) 和 cloud (PostgreSQL) 中共用同一套定义。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

import enum


# ──────────────────────────────────────────────────────────────────────────────
# 枚举
# ──────────────────────────────────────────────────────────────────────────────

class SubjectEnum(str, enum.Enum):
    math = "math"
    physics = "physics"
    chemistry = "chemistry"
    biology = "biology"
    history = "history"
    geography = "geography"
    politics = "politics"
    english = "english"
    chinese = "chinese"


class GradeEnum(str, enum.Enum):
    junior_1 = "junior_1"
    junior_2 = "junior_2"
    junior_3 = "junior_3"
    high_1 = "high_1"
    high_2 = "high_2"
    high_3 = "high_3"


class ErrorReasonEnum(str, enum.Enum):
    careless = "careless"           # 粗心大意
    concept_unclear = "concept_unclear"  # 概念不清
    formula_wrong = "formula_wrong" # 公式用错
    no_idea = "no_idea"             # 完全没思路
    other = "other"


class TaskStatusEnum(str, enum.Enum):
    pending = "pending"
    ocr_done = "ocr_done"
    awaiting_human = "awaiting_human"
    verified = "verified"
    analysis_done = "analysis_done"
    completed = "completed"
    failed = "failed"


# ──────────────────────────────────────────────────────────────────────────────
# 用户表
# ──────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=True)  # None for OAuth users
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    mistake_records: Mapped[list["UserMistakeRecord"]] = relationship(back_populates="user")
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    auth_providers: Mapped[list["AuthProvider"]] = relationship(back_populates="user")


# ──────────────────────────────────────────────────────────────────────────────
# 邮箱验证令牌表
# ──────────────────────────────────────────────────────────────────────────────

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ──────────────────────────────────────────────────────────────────────────────
# 用户扩展资料表（结构化属性）
# ──────────────────────────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=True)           # 年级
    strong_subjects: Mapped[str] = mapped_column(Text, nullable=True)       # JSON 数组
    weak_subjects: Mapped[str] = mapped_column(Text, nullable=True)         # JSON 数组
    learning_style: Mapped[str] = mapped_column(String(50), nullable=True)  # visual/auditory/etc
    personality_notes: Mapped[str] = mapped_column(Text, nullable=True)     # 自由文字
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="profile")


# ──────────────────────────────────────────────────────────────────────────────
# 第三方登录 Provider（Phase 2 预留：phone / wechat）
# ──────────────────────────────────────────────────────────────────────────────

class AuthProvider(Base):
    __tablename__ = "auth_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)       # email | phone | wechat
    provider_uid: Mapped[str] = mapped_column(String(200), nullable=False)  # 邮箱 / 手机号 / openid
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship(back_populates="auth_providers")



# ──────────────────────────────────────────────────────────────────────────────
# 错题处理任务表（生命周期跟踪）
# ──────────────────────────────────────────────────────────────────────────────

class QuestionTask(Base):
    """每次上传一张图片对应一条 Task 记录"""
    __tablename__ = "question_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="web")  # web | feishu | wecom
    status: Mapped[str] = mapped_column(String(30), default="pending")
    original_image_url: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# ──────────────────────────────────────────────────────────────────────────────
# 干净题目库（去重复用）
# ──────────────────────────────────────────────────────────────────────────────

class Question(Base):
    """去手写后的干净题目，多个学生可以共用同一道题"""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SHA256
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)   # 含 LaTeX
    clean_image_url: Mapped[str] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(30), nullable=True)
    grade: Mapped[str] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    mistake_records: Mapped[list["UserMistakeRecord"]] = relationship(back_populates="question")


# ──────────────────────────────────────────────────────────────────────────────
# 学生错题记录（核心业务表）
# ──────────────────────────────────────────────────────────────────────────────

class UserMistakeRecord(Base):
    __tablename__ = "user_mistake_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(36), nullable=True)

    # 学生手写部分
    wrong_answer_text: Mapped[str] = mapped_column(Text, nullable=True)  # 校对后的错答
    wrong_answer_image_url: Mapped[str] = mapped_column(Text, nullable=True)   # 手写截图

    # 人工标注
    error_reason: Mapped[str] = mapped_column(String(30), nullable=True)

    # AI 分析结果
    knowledge_nodes: Mapped[str] = mapped_column(Text, nullable=True)   # JSON 数组字符串
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=True)
    similar_keywords: Mapped[str] = mapped_column(Text, nullable=True)  # JSON 数组字符串

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship(back_populates="mistake_records")
    question: Mapped["Question"] = relationship(back_populates="mistake_records")


# ──────────────────────────────────────────────────────────────────────────────
# 知识点标签树
# ──────────────────────────────────────────────────────────────────────────────

class KnowledgeTag(Base):
    __tablename__ = "knowledge_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_tags.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=学科 2=章 3=节 4=考点


# ──────────────────────────────────────────────────────────────────────────────
# 订阅计划表（计费模块）
# ──────────────────────────────────────────────────────────────────────────────

class Subscription(Base):
    """用户当前有效订阅（每位用户最多一条有效记录）"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(20), nullable=False)        # trial | monthly | annual
    status: Mapped[str] = mapped_column(String(20), default="active")       # active | expired | cancelled
    activated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class ActivationKey(Base):
    """激活码使用记录（用于防止同一 Key 重复激活）"""
    __tablename__ = "activation_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nonce: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)   # SHA256(key)，用于审计
    note: Mapped[str] = mapped_column(String(200), nullable=True)           # 生成时的备注
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    used_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

