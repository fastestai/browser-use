# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv $VIRTUAL_ENV

# 安装 uv
RUN pip install uv

# 设置 PYTHONPATH
ENV PYTHONPATH=/app

# 复制依赖文件
COPY requirements.lock .

# 安装依赖
RUN uv pip install -r requirements.lock

# 复制其余项目文件
COPY . .

# 暴露端口
EXPOSE 18000

# 启动命令
CMD ["python", "-m", "src.api.server"] 