"""
billing/payment/base.py

支付渠道抽象基类。
所有支付渠道（微信支付、支付宝）必须实现此接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentOrder:
    """创建支付订单的请求"""
    order_id: str           # 内部订单 ID
    plan_id: str            # 套餐 ID
    amount_fen: int         # 金额（分）
    user_id: int
    description: str
    callback_url: str       # 支付结果回调 URL


@dataclass
class PaymentResult:
    """支付渠道回调结果"""
    success: bool
    order_id: str
    provider: str
    transaction_id: Optional[str] = None   # 渠道侧交易号
    message: str = ""


class PaymentProvider(ABC):
    """支付渠道统一抽象接口"""

    @abstractmethod
    def create_order(self, order: PaymentOrder) -> dict:
        """
        创建支付订单，返回前端需要的支付参数（如微信 JSAPI 参数、支付宝 form）。
        """
        ...

    @abstractmethod
    def verify_callback(self, raw_body: bytes, headers: dict) -> PaymentResult:
        """
        验证支付渠道回调通知的合法性并解析结果。
        """
        ...

    @abstractmethod
    def query_order(self, order_id: str) -> PaymentResult:
        """
        主动查询订单状态（补单/对账使用）。
        """
        ...
