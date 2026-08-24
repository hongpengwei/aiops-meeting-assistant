FROM python:3.11-slim

WORKDIR /app

# 安裝基本套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 設定時區為台北時間
ENV TZ=Asia/Taipei

COPY requirements.txt .
COPY requirements-extras.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 可選依賴：docker build --build-arg INSTALL_EXTRAS=true .
ARG INSTALL_EXTRAS=false
RUN if [ "$INSTALL_EXTRAS" = "true" ]; then pip install --no-cache-dir -r requirements-extras.txt; fi

COPY . .

# 預設啟動 Python 守護進程排程器
CMD ["python", "scheduler.py"]
