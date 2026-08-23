import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
from src.analytics.detector import AnomalyDetectionResult
from src.notifications.teams import TeamsNotifier
from src.notifications.email_sender import EmailNotifier

class ReportGenerator:
    """
    報告產生器與推播分派中心：負責將檢測結果與 AI 分析轉換為 Markdown / HTML 並推播
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notif_cfg = config.get("notifications", {})
        
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
        result: AnomalyDetectionResult, 
        ai_analyses: Dict[str, str]
    ) -> Tuple[str, str]:
        """
        產出報告並根據設定推播
        :return: (markdown_content, html_content)
        """
        meeting_name = "每日晨會" if result.mode == "daily" else "每週課會"
        status_emoji = "🔴 異常警報" if result.is_anomaly_detected else "🟢 一切正常"
        title = f"【{meeting_name}系統狀況報告】{status_emoji} ({result.target_period_str})"

        # 1. 產生 Markdown
        md_text = self._build_markdown(title, result, ai_analyses)

        # 2. 產生 HTML
        html_text = self._build_html(title, result, ai_analyses)

        # 3. 本地儲存
        if self.local_enabled:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_path = os.path.join(self.output_dir, f"{result.mode}_report_{timestamp_str}.md")
            html_path = os.path.join(self.output_dir, f"{result.mode}_report_{timestamp_str}.html")
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_text)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_text)
            
            print(f"[Reporter] 📄 本地報告已產生:")
            print(f"  - Markdown: {os.path.abspath(md_path)}")
            print(f"  - HTML:     {os.path.abspath(html_path)}")

        # 4. Teams 推播
        self.teams_notifier.send_message(
            title=title, 
            text_markdown=md_text, 
            is_anomaly=result.is_anomaly_detected
        )

        # 5. Email 發信
        self.email_notifier.send_report(
            subject=title,
            html_content=html_text,
            text_content=md_text
        )

        return md_text, html_text

    def _build_markdown(self, title: str, result: AnomalyDetectionResult, ai_analyses: Dict[str, str]) -> str:
        meeting_name = "每日晨會" if result.mode == "daily" else "每週課會"
        lines = [
            f"# {title}\n",
            f"- **會議類型**：{meeting_name}",
            f"- **統計目標**：{result.target_period_str}",
            f"- **比較基準**：{result.baseline_period_str}",
            f"- **總體狀態**：{'⚠️ 偵測到異常數量暴增' if result.is_anomaly_detected else '✅ 所有系統數量均在基準線內，運作正常'}\n",
            "## 📊 各系統 Case 數量統計表\n",
            "| 系統名稱 | 目標期數量 | 基準平均 | 增長率 | 狀態 |",
            "| :--- | :---: | :---: | :---: | :--- |"
        ]

        for s in result.systems:
            status_tag = "🔴 **異常暴增**" if s.is_anomaly else "🟢 正常"
            growth_str = f"{s.growth_rate:+.0f}%" if s.target_count > 0 or s.baseline_avg > 0 else "0%"
            lines.append(f"| `{s.system_name}` | {s.target_count} 件 | {s.baseline_avg:.1f} 件 | {growth_str} | {status_tag} |")

        if not result.is_anomaly_detected:
            lines.append("\n> 💡 **會前結論**：昨日/當週各系統工單量平穩，無特定機台或廠區之突發異常，會議可直接快速通過。")
        else:
            lines.append("\n---\n## 🤖 AI 深度歸因分析與會議發言重點\n")
            for sys_name, analysis in ai_analyses.items():
                lines.append(f"### 系統：`{sys_name}`\n")
                lines.append(analysis)
                lines.append("\n---\n")

        return "\n".join(lines)

    def _build_html(self, title: str, result: AnomalyDetectionResult, ai_analyses: Dict[str, str]) -> str:
        meeting_name = "每日晨會" if result.mode == "daily" else "每週課會"
        status_badge = '<span style="background-color:#d93025;color:white;padding:4px 8px;border-radius:4px;font-size:14px;">🔴 異常警報</span>' if result.is_anomaly_detected else '<span style="background-color:#1e8e3e;color:white;padding:4px 8px;border-radius:4px;font-size:14px;">🟢 運作正常</span>'

        rows_html = ""
        for s in result.systems:
            bg_color = "#fce8e6" if s.is_anomaly else "#ffffff"
            tag = '<b style="color:#d93025;">🔴 異常暴增</b>' if s.is_anomaly else '<span style="color:#1e8e3e;">🟢 正常</span>'
            growth_str = f"{s.growth_rate:+.0f}%" if s.target_count > 0 or s.baseline_avg > 0 else "0%"
            rows_html += f"""
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #e0e0e0;">
                <td style="padding: 10px; font-weight: bold;">{s.system_name}</td>
                <td style="padding: 10px; text-align: center;">{s.target_count} 件</td>
                <td style="padding: 10px; text-align: center;">{s.baseline_avg:.1f} 件</td>
                <td style="padding: 10px; text-align: center;">{growth_str}</td>
                <td style="padding: 10px; text-align: center;">{tag}</td>
            </tr>
            """

        ai_section_html = ""
        if result.is_anomaly_detected:
            ai_section_html += '<h2 style="color:#1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 6px;">🤖 AI 深度歸因分析與會議發言重點</h2>'
            for sys_name, analysis in ai_analyses.items():
                formatted_analysis = analysis.replace("\n", "<br>")
                ai_section_html += f"""
                <div style="background-color: #f8f9fa; border-left: 4px solid #1a73e8; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                    <h3 style="margin-top:0; color:#202124;">系統：<span style="color:#d93025;">{sys_name}</span></h3>
                    <div style="line-height: 1.6; color: #3c4043;">
                        {formatted_analysis}
                    </div>
                </div>
                """
        else:
            ai_section_html = """
            <div style="background-color: #e6f4ea; border-left: 4px solid #1e8e3e; padding: 15px; border-radius: 4px; color: #137333;">
                <b>💡 會前結論：</b> 各系統案件數量均在正常範圍內，無需特別關注事項，會議可快速通過。
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f1f3f4; margin: 0; padding: 20px; color: #202124; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}
        .header {{ border-bottom: 1px solid #dadce0; padding-bottom: 15px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th {{ background-color: #f8f9fa; border-bottom: 2px solid #dadce0; padding: 12px 10px; text-align: center; color: #5f6368; }}
        th:first-child {{ text-align: left; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0 0 10px 0; font-size: 22px;">{title}</h1>
            <div style="margin-top: 10px; font-size: 14px; color: #5f6368;">
                <span>📅 <b>會議類型</b>：{meeting_name}</span> | 
                <span>🎯 <b>統計目標</b>：{result.target_period_str}</span> | 
                <span>📈 <b>基準期間</b>：{result.baseline_period_str}</span>
            </div>
        </div>

        <h2>📊 各系統 Case 數量統計表</h2>
        <table>
            <thead>
                <tr>
                    <th>系統名稱</th>
                    <th>目標期數量</th>
                    <th>基準平均</th>
                    <th>增長率</th>
                    <th>狀態</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        {ai_section_html}

        <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #dadce0; font-size: 12px; color: #80868b; text-align: right;">
            由 Ops Insight Assistant 自動生成 • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""
        return html
