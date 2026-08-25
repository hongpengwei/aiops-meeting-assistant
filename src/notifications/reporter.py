import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Union
from jinja2 import Environment, FileSystemLoader
from src.analytics.detector import AnomalyDetectionResult, MonthlyDetectionResult
from src.notifications.teams import TeamsNotifier
from src.notifications.email_sender import EmailNotifier

logger = logging.getLogger(__name__)


class ReportRenderer:
    """
    報告渲染器：負責將檢測結果與 AI 分析轉換為 Markdown / HTML
    (單一職責：只負責模板渲染，不涉及推播)
    """

    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        try:
            import markdown
            self.env.filters["markdown"] = lambda text: markdown.markdown(text)
        except ImportError:
            self.env.filters["markdown"] = lambda text: text.replace("\n", "<br>")

    def render_markdown(
        self, 
        title: str, 
        meeting_name: str, 
        result: Union[AnomalyDetectionResult, MonthlyDetectionResult], 
        ai_analyses: Dict[str, str]
    ) -> str:
        template_name = "monthly_report.md.j2" if result.mode == "monthly" else "report.md.j2"
        template = self.env.get_template(template_name)
        return template.render(
            title=title,
            meeting_name=meeting_name,
            result=result,
            ai_analyses=ai_analyses
        )

    def render_html(
        self, 
        title: str, 
        meeting_name: str, 
        result: Union[AnomalyDetectionResult, MonthlyDetectionResult], 
        ai_analyses: Dict[str, str]
    ) -> str:
        template_name = "monthly_report.html.j2" if result.mode == "monthly" else "report.html.j2"
        template = self.env.get_template(template_name)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return template.render(
            title=title,
            meeting_name=meeting_name,
            result=result,
            ai_analyses=ai_analyses,
            current_time=current_time
        )


class ReportGenerator:
    """
    報告產生器與推播分派中心：協調渲染與通知推播
    (單一職責：只負責協調流程與推播，渲染委派給 ReportRenderer)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notif_cfg = config.get("notifications", {})
        
        # 渲染器
        self.renderer = ReportRenderer()

        # 本地輸出
        self.local_enabled = self.notif_cfg.get("local", {}).get("enabled", True)
        self.output_dir = self.notif_cfg.get("local", {}).get("output_dir", "./output")
        os.makedirs(self.output_dir, exist_ok=True)

        # Teams 推播
        teams_cfg = self.notif_cfg.get("teams", {})
        self.teams_notifier = TeamsNotifier(
            webhook_url=teams_cfg.get("webhook_url", ""),
            enabled=teams_cfg.get("enabled", False)
        )

        # Email 推播
        self.email_notifier = EmailNotifier(config)

    def generate_and_dispatch(
        self, 
        result: Union[AnomalyDetectionResult, MonthlyDetectionResult], 
        ai_analyses: Dict[str, str]
    ) -> Tuple[str, str]:
        """
        產出報告並根據設定推播
        :return: (markdown_content, html_content)
        """
        if result.mode == "daily":
            meeting_name = "每日晨會"
        elif result.mode == "weekly":
            meeting_name = "每週課會"
        else:
            meeting_name = "每月課會"

        status_emoji = "🔴 異常警報" if result.is_anomaly_detected else "🟢 一切正常"
        title = f"【{meeting_name}系統狀況報告】{status_emoji} ({result.target_period_str})"

        # 1. 渲染報告
        md_text = self.renderer.render_markdown(title, meeting_name, result, ai_analyses)
        html_text = self.renderer.render_html(title, meeting_name, result, ai_analyses)

        # 2. 本地儲存
        if self.local_enabled:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_path = os.path.join(self.output_dir, f"{result.mode}_report_{timestamp_str}.md")
            html_path = os.path.join(self.output_dir, f"{result.mode}_report_{timestamp_str}.html")
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_text)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_text)
            
            logger.info(f"[Reporter] 📄 本地報告已產生:")
            logger.info(f"  - Markdown: {os.path.abspath(md_path)}")
            logger.info(f"  - HTML:     {os.path.abspath(html_path)}")

        # 3. Teams 推播
        self.teams_notifier.send_message(
            title=title, 
            text_markdown=md_text, 
            is_anomaly=result.is_anomaly_detected
        )

        # 4. Email 發信
        self.email_notifier.send_report(
            subject=title,
            html_content=html_text,
            text_content=md_text
        )

        return md_text, html_text

