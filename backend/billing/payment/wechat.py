"""
billing/payment/wechat.py

微信支付适配器（Stub — 待接入微信支付 SDK）。

接入时需要：
  pip install wechatpayv3
  .env:
    WECHAT_PAY_MCH_ID=
    WECHAT_PAY_API_V3_KEY=
    WECHAT_PAY_APP_ID=
    WECHAT_PAY_PRIVATE_KEY_PATH=
"""
from __future__ import annotations

from .base import PaymentProvider, PaymentOrder, PaymentResult


class WechatPayProvider(PaymentProvider):
    """微信支付 v3 适配器（待实现）"""

    def __init__(self):
        # TODO: 从 config/settings.yaml 或 .env 加载微信支付配置
        # import os
        # self.mch_id = os.environ.get("WECHAT_PAY_MCH_ID", "")
        # self.api_v3_key = os.environ.get("WECHAT_PAY_API_V3_KEY", "")
        raise NotImplementedError(
            "微信支付尚未接入。接入时请实现 billing/payment/wechat.py"
        )

    def create_order(self, order: PaymentOrder) -> dict:
        # TODO: 调用微信支付 JSAPI 下单接口
        # https://pay.weixin.qq.com/docs/merchant/apis/jsapi-payment/direct-jsons/jsapi-prepay.html
        raise NotImplementedError

    def verify_callback(self, raw_body: bytes, headers: dict) -> PaymentResult:
        # TODO: 验证微信支付回调通知签名
        raise NotImplementedError

    def query_order(self, order_id: str) -> PaymentResult:
        # TODO: 微信支付查单接口
        raise NotImplementedError
