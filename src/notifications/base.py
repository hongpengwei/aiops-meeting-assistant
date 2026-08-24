from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    通知發送器的抽象基類 (Notification Adapter Pattern)
    所有通知管道（Teams, Email, Slack 等）都必須實作此介面
    """

    @abstractmethod
    def send(self, subject: str, content: str, is_anomaly: bool = False) -> bool:
        """
        發送通知

        :param subject: 通知標題
        :param content: 通知內容 (Markdown 或純文字)
        :param is_anomaly: 是否為異常警報 (影響通知樣式/優先級)
        :return: 是否發送成功
        """
        pass
