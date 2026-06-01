# Atlas Agent — Docker 镜像
# 多阶段构建: 生产镜像仅包含运行时依赖

# ── Stage 1: Build ───────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制项目文件
COPY pyproject.toml setup.py README.md ./
COPY atlas_core/ atlas_core/

# 安装依赖并构建 wheel
RUN uv pip install build --system && \
    python -m build --wheel

# ── Stage 2: Runtime ─────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 从 builder 复制 wheel
COPY --from=builder /build/dist/*.whl .

# 安装 Atlas
RUN pip install --no-cache-dir *.whl && \
    rm -f *.whl

# 暴露 WebUI 端口
EXPOSE 8640

# 默认入口: CLI 交互模式
ENTRYPOINT ["atlas"]
CMD ["--help"]
