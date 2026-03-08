# 使用固定版本的 slim 镜像，保证构建稳定性
FROM python:3.12.7-slim-bookworm

RUN useradd -u 1000 -m appuser

# 安装必要的系统依赖（uv 安装脚本需要 curl，可选：清理缓存减小镜像体积）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set uv link mode to copy to avoid hardlink warnings
ENV UV_LINK_MODE=copy

# 设置 pip 国内镜像
RUN pip3 install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 非root用户运行
USER appuser