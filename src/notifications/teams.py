import requests
from typing import Optional

class TeamsNotifier:
    """
    Microsoft Teams Webhook 發送器 (支援 Incoming Webhook MessageCard)
    """

    def __init__(self, webhook_url: str, enabled: bool = True):
        self.webhook_url = webhook_url
        self.enabled = enabled

    def send_message(self, title: str, text_markdown: str, is_anomaly: bool = False) -> bool:
        if not self.enabled or not self.webhook_url:
            print("[Teams Notifier] ℹ️ Teams 推播未啟用或未設定 webhook_url，略過發送。")
            return False

        # 根據狀態決定卡片頂部顏色條 (綠色正常 / 紅色異常)
        theme_color = "EA4335" if is_anomaly else "34A853"

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": title,
            "sections": [
                {
                    "activityTitle": f"**{title}**",
                    "activitySubtitle": "🤖 晨會 / 課會 AIOps 智能監控助手",
                    "text": text_markdown,
                    "markdown": True
                }
            ]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=15)
            if response.status_code == 200:
                print("[Teams Notifier] ✅ Teams 訊息發送成功！")
                return True
            else:
                print(f"[Teams Notifier] ⚠️ Teams 發送失敗: HTTP {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[Teams Notifier] ❌ Teams 發送錯誤: {e}")
            return False
