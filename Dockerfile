# syntax=docker/dockerfile:1.6

# --- 全局变量声明：必须在第一个 FROM 之前，防止变量为空报错 ---
ARG BUILDPLATFORM=linux/amd64
ARG TARGETPLATFORM=linux/arm64
ARG HAILO_VERSION="4.23.0"

############################
# Stage 1: Build Stage (编译阶段)
############################
# 使用 --platform=$BUILDPLATFORM 充分利用 GitHub Runner 的 x86 性能
FROM --platform=$BUILDPLATFORM python:3.13-slim AS build

# 在阶段内重新引入变量使其可用
ARG TARGETPLATFORM
ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装编译所需的完整工具链
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    cmake \
    build-essential \
    autoconf \
    automake \
    unzip \
    zip \
    python3-dev \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

# 升级基础构建工具
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 1. 下载并编译 HailoRT C++ 库 (arm64)
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install --parallel $(nproc)

# 2. 预编译所有 Python 依赖 (包括 netifaces, opencv, numpy 等)
WORKDIR /wheels
COPY requirements.txt .
# 虽然在 x86 上运行，但 pip 会根据 TARGETPLATFORM 生成 arm64 的 wheel
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 HailoRT Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage (运行阶段)
############################
# 最终生成的镜像是针对树莓派 arm64 的
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 安装运行期最小依赖，不含 gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    libglib2.0-0 \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝 HailoRT 二进制文件
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
# 拷贝所有编译好的 .whl 文件
COPY --from=build /wheels /tmp/wheels

# 关键修复：使用 --no-index 强制只从本地找 Wheel，防止因缺失 gcc 导致的编译失败
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .

# 确保库加载路径包含 /usr/local/lib
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

EXPOSE 8000
CMD ["python3", "run_api.py"]
