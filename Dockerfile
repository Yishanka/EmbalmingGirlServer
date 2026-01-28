# 使用轻量级基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，确保 Python 输出直接打印到日志
ENV PYTHONUNBUFFERED=1

# 先只复制依赖文件，利用 Docker 缓存
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码（假设你的代码在当前目录或 backend 目录下）
# 如果你的主入口是 backend/main.py，根据实际路径调整
COPY . .

# 微信云托管默认监听 80 端口
EXPOSE 80

# 启动 FastAPI。注意：host 必须是 0.0.0.0，port 必须是 80
# 生产环境建议开启 proxy_headers 处理微信转发的头信息
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]