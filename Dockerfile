FROM python:3.11-slim

WORKDIR /app

# 安裝基本套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 設定時區為台北時間
ENV TZ=Asia/Taipei

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 預設啟動 Python 守護進程排程器
CMD ["python", "scheduler.py"]
