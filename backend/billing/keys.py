"""
billing/keys.py

激活码生成与验证（HMAC-SHA256 签名，无需数据库即可验证）。

Key 格式（Base64URL 编码）：
  {plan}|{expires_iso}|{nonce}|{hmac_hex}

例：
  monthly|2026-03-21T13:42:00|a3f9|<hmac>

密钥来源：环境变量 BILLING_SECRET（配置在 .env 中）。

用法（CLI）：
  python3 -m billing.keygen --plan monthly
  python3 -m billing.keygen --plan trial
  python3 -m billing.keygen --plan annual --note "VIP-001"
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from .plans import get_plan, Plan

# ── 内部工具 ─────────────────────────────────────────────────


def _get_secret() -> bytes:
    secret = os.environ.get("BILLING_SECRET", "")
    if not secret:
        raise RuntimeError(
            "BILLING_SECRET 未设置！请在 backend/.env 中配置：\n"
            "  BILLING_SECRET=your-random-32+-character-string"
        )
    return secret.encode()


def _sign(payload: str) -> str:
    return hmac.new(_get_secret(), payload.encode(), hashlib.sha256).hexdigest()


def _b64url_encode(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _b64url_decode(s: str) -> str:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding).decode()


# ── Key 生成 ──────────────────────────────────────────────────


def generate_key(plan_id: str, note: str = "") -> str:
    """
    生成一个激活码。

    Args:
        plan_id: 'trial' | 'monthly' | 'annual'
        note:    可选备注（如 'VIP-001'），不影响验证逻辑

    Returns:
        可打印的激活码字符串（Base64URL 编码）
    """
    plan = get_plan(plan_id)
    now = datetime.now(timezone.utc)
    # Key 本身不嵌入 expires，由激活时的当前时间 + plan.duration_days 计算
    # 但记录生成时间，以便审计
    nonce = secrets.token_hex(4)                 # 8 chars 随机数，防重放
    created_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
    note_part = note.replace("|", "-")           # 防止分隔符冲突

    payload = f"{plan_id}|{created_iso}|{nonce}|{note_part}"
    sig = _sign(payload)
    raw = f"{payload}|{sig}"
    return _b64url_encode(raw)


# ── Key 验证 ──────────────────────────────────────────────────


class KeyValidationError(Exception):
    pass


def verify_key(key: str) -> dict:
    """
    验证激活码合法性（离线，无需数据库）。

    Returns:
        dict: { plan_id, plan, created_at, nonce, note }

    Raises:
        KeyValidationError: key 格式错误或签名无效
    """
    try:
        raw = _b64url_decode(key)
    except Exception:
        raise KeyValidationError("激活码格式错误")

    parts = raw.split("|")
    if len(parts) != 5:
        raise KeyValidationError("激活码格式错误（字段数不匹配）")

    plan_id, created_iso, nonce, note, provided_sig = parts

    # 验证签名
    payload = f"{plan_id}|{created_iso}|{nonce}|{note}"
    expected_sig = _sign(payload)
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise KeyValidationError("激活码签名无效")

    # 验证套餐合法性
    plan = get_plan(plan_id)  # 会抛出 ValueError 如果 plan_id 不合法

    return {
        "plan_id": plan_id,
        "plan": plan,
        "created_at": created_iso,
        "nonce": nonce,
        "note": note,
    }
