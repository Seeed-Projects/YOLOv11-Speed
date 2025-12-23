# syntax=docker/dockerfile:1.6

############################
# Stage 1: build hailort
############################
ARG BUILDPLATFORM
FROM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    cmake \
    build-essential \
    autoconf \
    automake \
    unzip \
    zip \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

# Build hailort
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git

WORKDIR /tmp/hailort
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build --target install

# Build Python wheel
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: runtime-only
############################
ARG TARGETPLATFORM
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE

# ⚠️ 只安装运行期必需的库
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy hailort runtime artifacts
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
COPY --from=build /wheels /wheels

# Python deps
WORKDIR /app
COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir /wheels/*.whl \
 && rm -rf /wheels

# App
COPY . .

EXPOSE 8000
CMD ["python3", "run_api.py"]
