#!/usr/bin/env python3
"""
keygen_standalone.py

独立激活码生成脚本，无需依赖任何项目模块。
可在任何地方运行，只需设置 BILLING_SECRET 环境变量。

用法：
  export BILLING_SECRET=your-secret-key
  python3 keygen_standalone.py --plan monthly --count 3
  python3 keygen_standalone.py --plan trial --note "测试用户"
  python3 keygen_standalone.py --plan annual --count 10

套餐说明：
  trial   → 9.90 元 / 7天 / 最多20道错题
  monthly → 49.00 元 / 30天 / 无限制
  annual  → 399.00 元 / 365天 / 无限制
"""
import argparse
import base64
import hashlib
import hmac
import os
import secrets
import sys
from datetime import datetime, timezone

PLANS = {
    "trial":   {"name": "试用版",   "price": "9.90",   "days": 7,   "limit": "20道"},
    "monthly": {"name": "月度会员", "price": "49.00",  "days": 30,  "limit": "无限"},
    "annual":  {"name": "年度会员", "price": "399.00", "days": 365, "limit": "无限"},
}


def _get_secret() -> bytes:
    s = os.environ.get("BILLING_SECRET", "")
    if not s:
        print("❌ 错误：未设置 BILLING_SECRET 环境变量", file=sys.stderr)
        print("   export BILLING_SECRET=your-secret-key", file=sys.stderr)
        sys.exit(1)
    return s.encode()


def _sign(payload: str) -> str:
    return hmac.new(_get_secret(), payload.encode(), hashlib.sha256).hexdigest()


def generate_key(plan_id: str, note: str = "") -> str:
    nonce = secrets.token_hex(4)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    note = note.replace("|", "-")
    payload = f"{plan_id}|{created}|{nonce}|{note}"
    sig = _sign(payload)
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def main():
    parser = argparse.ArgumentParser(description="TipToro 激活码生成工具")
    parser.add_argument("--plan", required=True, choices=list(PLANS), help="套餐类型")
    parser.add_argument("--note", default="", help="备注（可选）")
    parser.add_argument("--count", type=int, default=1, help="生成数量")
    args = parser.parse_args()

    plan = PLANS[args.plan]
    print(f"\n📦 {plan['name']}  {plan['price']}元 / {plan['days']}天 / {plan['limit']}")
    print("─" * 60)
    for i in range(args.count):
        note = f"{args.note}-{i+1}" if args.count > 1 and args.note else args.note
        print(generate_key(args.plan, note=note))
    print("─" * 60)
    print(f"✅ 已生成 {args.count} 个激活码\n")


if __name__ == "__main__":
    main()
