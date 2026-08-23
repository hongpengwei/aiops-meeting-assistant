import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Email (SMTP) 發信模組
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("notifications", {}).get("email", {})
        self.enabled = self.cfg.get("enabled", False)
        self.smtp_host = self.cfg.get("smtp_host", "localhost")
        self.smtp_port = self.cfg.get("smtp_port", 587)
        self.use_tls = self.cfg.get("use_tls", True)
        self.sender = self.cfg.get("sender", "ops-assistant@company.com")
        self.recipients = self.cfg.get("recipients", [])
        
        user_env = self.cfg.get("username_env_var", "SMTP_USER")
        pass_env = self.cfg.get("password_env_var", "SMTP_PASSWORD")
        self.username = os.getenv(user_env, "")
        self.password = os.getenv(pass_env, "")

    def send_report(self, subject: str, html_content: str, text_content: str = "") -> bool:
        if not self.enabled or not self.recipients:
            logger.info("[Email Notifier] ℹ️ Email 發信未啟用或未設定收件人，略過發信。")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            logger.info(f"[Email Notifier] ✅ 郵件發送成功至: {', '.join(self.recipients)}")
            return True
        except Exception as e:
            logger.error(f"[Email Notifier] ❌ 郵件發送失敗: {e}")
            return False
