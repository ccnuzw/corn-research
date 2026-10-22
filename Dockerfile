# ============================================
# 玉米研究系统V2 - Docker镜像
# 多阶段构建：Rust后端 + Python采集器
# ============================================

# ============================================
# Stage 1: Rust构建环境
# ============================================
FROM rust:bookworm as rust-builder

WORKDIR /build

# 安装Python 3（使用系统默认版本）
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 复制Rust项目文件和锁定文件
COPY backend-rust ./backend-rust/
COPY core-rust ./core-rust/

# 使用 --locked 标志构建，强制使用 Cargo.lock 中的版本
RUN cd backend-rust && \
    cargo build --release --locked && \
    strip target/release/corn-backend

# ============================================
# Stage 2: 运行时环境
# ============================================
FROM debian:bookworm-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制Rust二进制
COPY --from=rust-builder /build/backend-rust/target/release/corn-backend /usr/local/bin/

# 复制Python采集器
COPY collectors-python /app/collectors-python
RUN pip3 install --no-cache-dir --break-system-packages \
    requests \
    beautifulsoup4 \
    lxml \
    'redis>=5.0,<6' \
    'tenacity>=8.2,<10'

# 创建数据目录
RUN mkdir -p /app/data

# 环境变量
ENV RUST_LOG=info
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["corn-backend"]
