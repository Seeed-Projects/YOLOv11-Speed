# syntax=docker/dockerfile:1.6

############################
# Stage 1: Build Stage (编译阶段)
############################
ARG BUILDPLATFORM
# 使用 slim-bookworm 或 slim (trixie) 均可，这里统一处理编译环境
FROM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建必需的工具
# 包含编译 HailoRT 和从源码构建 Python 依赖（如 NumPy）所需的工具链
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

# 1. 下载并编译 HailoRT C++ 库
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install

# 2. 预编译 Python 依赖包 (Wheels)
# 在 build 阶段利用编译工具链提前解决 NumPy 等包的源码编译问题
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 HailoRT Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage (运行阶段)
############################
ARG TARGETPLATFORM
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 安装运行期最小依赖
# 修复 libglib2.0-0 在新版 Debian (Trixie) 中的包名问题
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    libglib2.0-0t64 \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝 HailoRT 二进制库和工具
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
# 拷贝所有预编译好的 Python .whl 文件
COPY --from=build /wheels /tmp/wheels

# 安装所有编译好的依赖，并更新共享库缓存
RUN pip install --no-cache-dir /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .

EXPOSE 8000
# 建议使用 python3 确保路径正确
CMD ["python3", "run_api.py"]
