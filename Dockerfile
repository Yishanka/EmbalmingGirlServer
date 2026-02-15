FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# --- 新增：安装构建工具 ---
# build-essential 提供 gcc/g++, python3-dev 提供头文件
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]