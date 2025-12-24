# syntax=docker/dockerfile:1.6

# --- 全局变量声明 ---
ARG TARGETPLATFORM=linux/arm64
ARG HAILO_VERSION="4.23.0"

############################
# Stage 1: Build Stage
############################
# 使用 TARGETPLATFORM 确保在模拟环境下生成 100% 兼容的 arm64 依赖
FROM --platform=$TARGETPLATFORM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建必需工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git cmake build-essential \
    autoconf automake unzip zip python3-dev pkg-config \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 1. 下载并编译 HailoRT C++ 库
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install --parallel $(nproc)

# 2. 预编译项目依赖包
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 关键修复：编译 HailoRT 绑定及其隐藏依赖 (如 argcomplete)
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
# 此步骤会扫描 setup.py 并将缺失的依赖下载编译为 wheel 存入 /wheels
RUN pip wheel --no-cache-dir --wheel-dir=/wheels .
# 生成 hailort 自身的 wheel
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 安装运行期最小依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libstdc++6 libgcc-s1 libglib2.0-0 libgl1 curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝 HailoRT 二进制成果
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
# 拷贝所有预编译好的 .whl 文件 (现在包含了 argcomplete)
COPY --from=build /wheels /tmp/wheels

# 强制使用本地 Wheels 安装
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .
