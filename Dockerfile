# syntax=docker/dockerfile:1.6

# --- 全局变量声明 ---
ARG TARGETPLATFORM=linux/arm64
ARG HAILO_VERSION="4.23.0"

############################
# Stage 1: Build Stage (编译阶段)
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建必需的系统工具
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

# 2. 预编译项目 requirements.txt 中的依赖
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 核心修复：自动解析并打包 HailoRT Python 绑定的依赖 (如 argcomplete)
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN pip wheel --no-cache-dir --wheel-dir=/wheels .
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage (运行阶段)
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装运行期最小依赖库
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libstdc++6 libgcc-s1 libglib2.0-0 libgl1 curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝 HailoRT 二进制库
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
# 拷贝所有预编译好的 .whl 文件
COPY --from=build /wheels /tmp/wheels

# 4. 强制离线安装，确保不触发源码编译
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .

# 暴露端口 (根据 app.py 中的设置)
EXPOSE 5000

# 5. 设置启动指令，防止进入 Python 交互界面
# 假设您的入口文件是项目根目录下的 app.py
CMD ["python3", "run_api.py"]
