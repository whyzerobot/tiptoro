"""
auth/jwt.py

JWT 签发与校验。
密钥来自环境变量 JWT_SECRET（必须在 .env 中配置）。
依赖：pip install PyJWT
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

_SECRET: Optional[str] = None
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7   # 7 天
REFRESH_MARGIN_HOURS = 24             # 剩余 24h 内自动续签


def _get_secret() -> str:
    global _SECRET
    if not _SECRET:
        _SECRET = os.environ.get("JWT_SECRET", "")
        if not _SECRET:
            raise RuntimeError(
                "JWT_SECRET 未设置！请在 .env 中配置：JWT_SECRET=your-secure-random-key"
            )
    return _SECRET


def create_token(payload: dict, expires_hours: int = ACCESS_TOKEN_EXPIRE_HOURS) -> str:
    """签发 JWT，payload 中会自动注入 exp / iat"""
    now = datetime.now(timezone.utc)
    data = {
        **payload,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
    }
    return jwt.encode(data, _get_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码并校验 JWT。
    - 过期抛出 jwt.ExpiredSignatureError
    - 无效签名抛出 jwt.InvalidTokenError
    """
    return jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])


def create_access_token(user_id: int, email: str) -> str:
    return create_token({"sub": str(user_id), "email": email, "type": "access"})
