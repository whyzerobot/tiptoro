"""
billing/payment/alipay.py

支付宝适配器（Stub — 待接入支付宝 SDK）。

接入时需要：
  pip install alipay-sdk-python
  .env:
    ALIPAY_APP_ID=
    ALIPAY_PRIVATE_KEY=
    ALIPAY_PUBLIC_KEY=
"""
from __future__ import annotations

from .base import PaymentProvider, PaymentOrder, PaymentResult


class AlipayProvider(PaymentProvider):
    """支付宝适配器（待实现）"""

    def __init__(self):
        # TODO: 从 .env 加载支付宝配置
        # import os
        # self.app_id = os.environ.get("ALIPAY_APP_ID", "")
        raise NotImplementedError(
            "支付宝尚未接入。接入时请实现 billing/payment/alipay.py"
        )

    def create_order(self, order: PaymentOrder) -> dict:
        # TODO: 调用支付宝 alipay.trade.page.pay 或 alipay.trade.app.pay
        # https://opendocs.alipay.com/open/270/105898
        raise NotImplementedError

    def verify_callback(self, raw_body: bytes, headers: dict) -> PaymentResult:
        # TODO: 验证支付宝异步通知签名
        raise NotImplementedError

    def query_order(self, order_id: str) -> PaymentResult:
        # TODO: alipay.trade.query
        raise NotImplementedError
