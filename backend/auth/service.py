"""
auth/service.py

核心鉴权服务：注册、登录、邮箱验证。
所有数据库操作通过 infra.database.get_session() 完成。
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from infra.database import get_session
from infra.models import User, EmailVerificationToken, UserProfile, AuthProvider
from auth.password import hash_password, verify_password
from auth.jwt import create_access_token
from auth.email import send_verification_email


# ──────────────────────────────────────────────────────────────
# 返回数据结构
# ──────────────────────────────────────────────────────────────

@dataclass
class AuthResult:
    success: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    message: str = ""


# ──────────────────────────────────────────────────────────────
# 注册
# ──────────────────────────────────────────────────────────────

def register(
    email: str,
    password: str,
    display_name: Optional[str] = None,
    base_url: str = "http://localhost:8000",
) -> AuthResult:
    """
    注册新用户。
    - 检查邮箱是否已存在
    - 创建 User + UserProfile + AuthProvider 记录
    - 生成邮箱验证 token，调用邮件服务发送（local 环境打印到控制台）
    """
    email = email.strip().lower()

    with get_session() as session:
        existing = session.query(User).filter_by(email=email).first()
        if existing:
            return AuthResult(success=False, message="该邮箱已被注册")

        # 1. 创建用户
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name or email.split("@")[0],
            email_verified=False,
        )
        session.add(user)
        session.flush()  # 获取 user.id

        # 2. 创建空白用户资料
        profile = UserProfile(user_id=user.id)
        session.add(profile)

        # 3. 记录 email provider
        provider = AuthProvider(
            user_id=user.id,
            provider="email",
            provider_uid=email,
        )
        session.add(provider)

        # 4. 生成邮箱验证 token（24小时有效）
        token_str = secrets.token_urlsafe(32)
        verification = EmailVerificationToken(
            user_id=user.id,
            token=token_str,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        session.add(verification)
        session.flush()

        user_id = user.id
        user_email = user.email

    # 发送验证邮件（session 已 commit，在 session 外发送避免事务阻塞）
    send_verification_email(user_email, token_str, base_url=base_url)

    return AuthResult(
        success=True,
        user_id=user_id,
        email=user_email,
        message="注册成功！请查收验证邮件（local 模式：查看控制台输出）。",
    )


# ──────────────────────────────────────────────────────────────
# 邮箱验证
# ──────────────────────────────────────────────────────────────

def verify_email(token: str) -> AuthResult:
    """校验邮箱验证 token，成功后将 user.email_verified 置为 True"""
    with get_session() as session:
        record = session.query(EmailVerificationToken).filter_by(token=token, used=False).first()
        if not record:
            return AuthResult(success=False, message="验证链接无效或已使用")

        now = datetime.now(timezone.utc)
        # SQLite 存储的 datetime 无时区信息，需兼容处理
        expires = record.expires_at
        if expires.tzinfo is None:
            from datetime import timezone as tz
            expires = expires.replace(tzinfo=tz.utc)

        if now > expires:
            return AuthResult(success=False, message="验证链接已过期，请重新发送")

        record.used = True
        user = session.get(User, record.user_id)
        if not user:
            return AuthResult(success=False, message="用户不存在")
        user.email_verified = True

        return AuthResult(
            success=True,
            user_id=user.id,
            email=user.email,
            message="邮箱验证成功！",
        )


# ──────────────────────────────────────────────────────────────
# 登录
# ──────────────────────────────────────────────────────────────

def login(email: str, password: str) -> AuthResult:
    """
    登录验证。
    - 邮箱未验证时拒绝登录（安全策略：local 模式可跳过）
    - 返回 JWT access token
    """
    email = email.strip().lower()

    with get_session() as session:
        user = session.query(User).filter_by(email=email, is_active=True).first()
        if not user or not user.password_hash:
            return AuthResult(success=False, message="邮箱或密码错误")

        if not verify_password(password, user.password_hash):
            return AuthResult(success=False, message="邮箱或密码错误")

        if not user.email_verified:
            return AuthResult(
                success=False,
                message="邮箱尚未验证，请先完成邮箱验证后再登录",
            )

        token = create_access_token(user_id=user.id, email=user.email)
        return AuthResult(
            success=True,
            user_id=user.id,
            email=user.email,
            access_token=token,
            message="登录成功",
        )


# Phase 2 预留接口（当前为 stub）
def login_with_phone(phone: str, otp_code: str) -> AuthResult:
    """Phase 2: 手机号验证码登录（待实现）"""
    raise NotImplementedError("Phase 2 功能，待实现")


def login_with_wechat(code: str) -> AuthResult:
    """Phase 2: 微信 OAuth 登录（待实现）"""
    raise NotImplementedError("Phase 2 功能，待实现")
