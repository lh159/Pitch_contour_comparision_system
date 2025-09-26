# 音高曲线比对系统 Docker 配置文件
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    python3-dev \
    gcc \
    g++ \
    make \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads outputs temp static/css static/js static/images \
    data/cache/timestamps src/uploads src/temp src/outputs cache/tts

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_APP=web_interface.py
ENV FLASK_ENV=production
ENV PORT=5001

# 暴露端口
EXPOSE 5001

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/system/status || exit 1

# 启动应用
CMD ["python", "web_interface.py"]

