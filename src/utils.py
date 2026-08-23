import logging
import sys

def setup_logging():
    """設定基本日誌格式"""
    # 確保 StreamHandler 使用 UTF-8 (透過 sys.stdout 輸出)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

def fix_windows_encoding():
    """修復 Windows 下的 cp950 編碼問題"""
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def get_logger(name):
    """取得指定名稱的 logger"""
    return logging.getLogger(name)
