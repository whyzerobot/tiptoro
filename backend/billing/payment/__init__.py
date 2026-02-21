"""
billing/payment/__init__.py

支付渠道接口层。
当前所有渠道均为 stub，等接入真实 SDK 时在各子模块中实现。
"""
from .base import PaymentProvider, PaymentOrder, PaymentResult

__all__ = ["PaymentProvider", "PaymentOrder", "PaymentResult"]
