FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码 + 前端静态文件
COPY backend/ .

# Fly.io 会将持久卷挂载到 /data，DATA_DIR 环境变量指定数据库路径
ENV DATA_DIR=/data
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
