"""
billing/plans.py

套餐定义 — 所有计费逻辑的单一来源。
若需调整价格或限额，只改这里。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Plan:
    id: str                        # 套餐标识符：trial / monthly / annual
    name: str                      # 显示名称
    price_fen: int                 # 价格（分），0 表示免费
    duration_days: int             # 有效期（天）
    max_mistakes: Optional[int]    # 最大错题数，None 表示不限
    description: str               # 简短描述

    @property
    def price_yuan(self) -> str:
        """格式化人民币价格，如 '9.90'"""
        return f"{self.price_fen / 100:.2f}"

    @property
    def is_unlimited(self) -> bool:
        return self.max_mistakes is None


# ── 套餐注册表 ────────────────────────────────────────────────

PLANS: dict[str, Plan] = {
    "trial": Plan(
        id="trial",
        name="试用版",
        price_fen=990,          # 9.90 RMB
        duration_days=7,
        max_mistakes=20,
        description="7天试用，最多20道错题",
    ),
    "monthly": Plan(
        id="monthly",
        name="月度会员",
        price_fen=4900,         # 49.00 RMB
        duration_days=30,
        max_mistakes=None,      # 不限
        description="30天，无限错题",
    ),
    "annual": Plan(
        id="annual",
        name="年度会员",
        price_fen=39900,        # 399.00 RMB
        duration_days=365,
        max_mistakes=None,      # 不限
        description="365天，无限错题，最优惠",
    ),
}


def get_plan(plan_id: str) -> Plan:
    if plan_id not in PLANS:
        raise ValueError(f"未知套餐: {plan_id!r}，可选: {list(PLANS)}")
    return PLANS[plan_id]
