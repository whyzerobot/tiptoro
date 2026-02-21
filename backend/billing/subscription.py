"""
billing/subscription.py

订阅管理：激活码兑换为用户订阅，查询订阅状态，检查使用配额。
数据持久化通过 infra.database（infra/models.py 中的 Subscription 表）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from infra.database import get_session
from infra.models import Subscription, ActivationKey, UserMistakeRecord
from billing.keys import verify_key, KeyValidationError
from billing.plans import get_plan, Plan


# ── 响应数据结构 ─────────────────────────────────────────────────

@dataclass
class SubscriptionStatus:
    active: bool
    plan_id: Optional[str]
    plan_name: Optional[str]
    expires_at: Optional[datetime]
    days_remaining: Optional[int]
    mistakes_used: int
    mistakes_limit: Optional[int]   # None = 无限
    can_add_mistake: bool
    message: str


# ── 激活 ─────────────────────────────────────────────────────────

def activate_key(user_id: int, key: str) -> SubscriptionStatus:
    """
    用激活码为用户开通订阅。
    - 验证 Key 签名
    - 检查 Key 是否已被使用
    - 创建/更新用户订阅记录
    """
    # 1. 离线验证 Key 合法性
    try:
        key_info = verify_key(key)
    except KeyValidationError as e:
        return SubscriptionStatus(
            active=False, plan_id=None, plan_name=None,
            expires_at=None, days_remaining=None,
            mistakes_used=0, mistakes_limit=None,
            can_add_mistake=False, message=str(e),
        )

    plan = key_info["plan"]
    key_nonce = key_info["nonce"]

    with get_session() as session:
        # 2. 检查 Key 是否已被激活（通过 nonce 去重）
        existing_key = session.query(ActivationKey).filter_by(nonce=key_nonce).first()
        if existing_key and existing_key.used_by_user_id is not None:
            return SubscriptionStatus(
                active=False, plan_id=None, plan_name=None,
                expires_at=None, days_remaining=None,
                mistakes_used=0, mistakes_limit=None,
                can_add_mistake=False,
                message="此激活码已被使用",
            )

        # 3. 计算订阅有效期
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=plan.duration_days)

        # 4. 记录激活码使用
        if not existing_key:
            existing_key = ActivationKey(
                nonce=key_nonce,
                plan_id=plan.id,
                raw_key_hash=_hash_key(key),
                created_at=now,
                note=key_info.get("note", ""),
            )
            session.add(existing_key)
        existing_key.used_by_user_id = user_id
        existing_key.activated_at = now

        # 5. 创建/覆盖用户订阅（新订阅覆盖旧订阅）
        sub = session.query(Subscription).filter_by(user_id=user_id).first()
        if sub:
            sub.plan_id = plan.id
            sub.expires_at = expires_at
            sub.activated_at = now
            sub.status = "active"
        else:
            sub = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                expires_at=expires_at,
                activated_at=now,
                status="active",
            )
            session.add(sub)

    return get_status(user_id)


def _hash_key(key: str) -> str:
    import hashlib
    return hashlib.sha256(key.encode()).hexdigest()


# ── 状态查询 ─────────────────────────────────────────────────────

def get_status(user_id: int) -> SubscriptionStatus:
    """查询用户当前订阅状态和配额使用情况"""
    with get_session() as session:
        sub = session.query(Subscription).filter_by(user_id=user_id).first()

        # 无订阅
        if not sub:
            return SubscriptionStatus(
                active=False, plan_id=None, plan_name=None,
                expires_at=None, days_remaining=None,
                mistakes_used=0, mistakes_limit=0,
                can_add_mistake=False,
                message="暂无有效订阅，请激活激活码",
            )

        now = datetime.now(timezone.utc)
        expires = sub.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        # 检查是否过期
        if now > expires:
            return SubscriptionStatus(
                active=False,
                plan_id=sub.plan_id,
                plan_name=get_plan(sub.plan_id).name,
                expires_at=expires,
                days_remaining=0,
                mistakes_used=0, mistakes_limit=0,
                can_add_mistake=False,
                message="订阅已到期，请续费",
            )

        plan = get_plan(sub.plan_id)
        days_remaining = (expires - now).days

        # 统计错题数
        mistakes_used = session.query(UserMistakeRecord).filter_by(user_id=user_id).count()

        can_add = plan.is_unlimited or (mistakes_used < (plan.max_mistakes or 0))

        return SubscriptionStatus(
            active=True,
            plan_id=plan.id,
            plan_name=plan.name,
            expires_at=expires,
            days_remaining=days_remaining,
            mistakes_used=mistakes_used,
            mistakes_limit=plan.max_mistakes,
            can_add_mistake=can_add,
            message=f"{plan.name}，剩余 {days_remaining} 天",
        )


# ── 权限检查（供 API/Skill 调用）────────────────────────────────

def check_can_add_mistake(user_id: int) -> tuple[bool, str]:
    """
    快速检查用户是否可以新增错题。
    Returns: (can_add: bool, reason: str)
    """
    status = get_status(user_id)
    if not status.active:
        return False, status.message
    if not status.can_add_mistake:
        return False, f"试用版最多 {status.mistakes_limit} 道错题，请升级套餐"
    return True, "ok"
