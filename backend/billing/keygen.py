"""
billing/keygen.py

激活码生成命令行工具。

用法：
  cd /path/to/tiptoro
  BILLING_SECRET=your-secret python3 -m billing.keygen --plan trial
  BILLING_SECRET=your-secret python3 -m billing.keygen --plan monthly --note "VIP-2026"
  BILLING_SECRET=your-secret python3 -m billing.keygen --plan annual --count 5

参数：
  --plan    套餐类型：trial | monthly | annual（必填）
  --note    备注（可选，用于标识用途）
  --count   批量生成数量（默认 1）

输出：
  一行一个激活码，可直接发给用户或导入后台
"""
import argparse
import sys
import os
from pathlib import Path

# 确保从 tiptoro/backend/ 目录或 tiptoro/ 根目录均可运行
_here = Path(__file__).parent.parent  # backend/
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

# 直接导入，不走 billing/__init__.py（避免触发 infra DB 初始化）
from billing.plans import PLANS, get_plan   # noqa: E402
from billing.keys import generate_key       # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="TipToro 激活码生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 -m billing.keygen --plan trial
  python3 -m billing.keygen --plan monthly --note "邀请码-001"
  python3 -m billing.keygen --plan annual --count 10
        """,
    )
    parser.add_argument(
        "--plan",
        required=True,
        choices=list(PLANS.keys()),
        help=f"套餐类型：{', '.join(PLANS.keys())}",
    )
    parser.add_argument(
        "--note",
        default="",
        help="备注信息（如: VIP-001, 内测用户），不影响验证逻辑",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="批量生成数量（默认 1）",
    )

    args = parser.parse_args()

    # 检查环境变量
    if not os.environ.get("BILLING_SECRET"):
        print("❌ 错误：未设置 BILLING_SECRET 环境变量", file=sys.stderr)
        print("   设置方式：export BILLING_SECRET=your-secret-key", file=sys.stderr)
        sys.exit(1)

    plan = PLANS[args.plan]
    print(f"\n📦 套餐: {plan.name} ({plan.price_yuan} RMB / {plan.duration_days}天)", end="")
    if plan.max_mistakes:
        print(f" / 最多 {plan.max_mistakes} 道错题")
    else:
        print(" / 不限错题数")

    print(f"🔢 生成数量: {args.count}\n")
    print("─" * 60)

    for i in range(args.count):
        note = f"{args.note}-{i+1}" if args.count > 1 and args.note else args.note
        key = generate_key(args.plan, note=note)
        print(key)

    print("─" * 60)
    print(f"\n✅ 已生成 {args.count} 个激活码")
    print("   用户激活方式：登录 TipToro → 个人中心 → 激活码\n")


if __name__ == "__main__":
    main()
