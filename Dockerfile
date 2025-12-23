# syntax=docker/dockerfile:1.6

############################
# Stage 1: Build Stage
############################
ARG BUILDPLATFORM
FROM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建工具（用于编译 HailoRT 和可能的 NumPy 源码）
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
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

# 1. 编译 HailoRT
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install

# 2. 准备 Python Wheels
WORKDIR /wheels
COPY requirements.txt .

# 将 requirements 中的库打包成 wheel (解决 runtime 阶段缺少编译器的问题)
# 如果 numpy 1.26 没有 arm64 的现成包，这里会利用 build 阶段的 gcc 进行编译
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 HailoRT Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage
############################
ARG TARGETPLATFORM
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 只安装运行期必需的系统库
# 注意：opencv 可能需要 libgl1-mesa-glx 或 libglib2.0-0
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    libglib2.0-0 \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 从 build 阶段拷贝编译好的产物
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
COPY --from=build /wheels /tmp/wheels

# 安装所有预编译好的轮子 (包括 numpy, opencv, hailort 等)
RUN pip install --no-cache-dir /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 设置工作目录
WORKDIR /app
COPY . .

EXPOSE 8000
CMD ["python3", "run_api.py"]
