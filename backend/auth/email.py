"""
auth/email.py

邮箱服务：发送验证邮件。

- local 环境：不发真实邮件，把 token 打印到控制台（开发调试专用）
- cloud 环境：通过 SMTP 发送真实邮件

配置（config/settings.yaml）:
  auth:
    email_verification: true
    smtp:
      host: smtp.gmail.com
      port: 587
      from_address: noreply@tiptoro.app

密钥（.env）:
  SMTP_USER=your@email.com
  SMTP_PASSWORD=your-smtp-app-password
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.loader import app_settings


def send_verification_email(to_email: str, token: str, base_url: str = "http://localhost:8000") -> None:
    """
    发送邮箱验证邮件。
    local 环境下打印 token 到控制台，cloud 环境下真实发送。
    """
    verify_url = f"{base_url}/auth/verify-email?token={token}"

    if app_settings.active_env == "local":
        # 本地开发：直接打印，无需 SMTP
        print("\n" + "=" * 60)
        print(f"[DEV] 邮箱验证邮件（本地模式，仅打印不发送）")
        print(f"  收件人 : {to_email}")
        print(f"  验证链接: {verify_url}")
        print(f"  Token  : {token}")
        print("=" * 60 + "\n")
        return

    # cloud 环境：真实发送 SMTP
    smtp_cfg = app_settings._raw.get("smtp", {}) if hasattr(app_settings, "_raw") else {}
    host = smtp_cfg.get("host", "smtp.gmail.com")
    port = smtp_cfg.get("port", 587)
    from_addr = smtp_cfg.get("from_address", os.environ.get("SMTP_USER", ""))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "【TipToro】请验证您的邮箱"
    msg["From"] = from_addr
    msg["To"] = to_email

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>欢迎加入 TipToro！</h2>
      <p>请点击下方按钮验证您的邮箱地址：</p>
      <a href="{verify_url}"
         style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;
                border-radius:8px;text-decoration:none;font-weight:bold;">
        验证邮箱
      </a>
      <p style="color:#888;font-size:12px;">链接 24 小时内有效。若非本人操作，请忽略此邮件。</p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, to_email, msg.as_string())
