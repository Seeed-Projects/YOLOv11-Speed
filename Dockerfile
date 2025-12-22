# Stage 1: Build dependencies
ARG BUILD_FROM=python:3.13-slim
FROM ${BUILD_FROM} as build

ARG HAILO_VERSION
ARG MAKEFLAGS="-j2"

ENV \
    DEBIAN_FRONTEND=noninteractive \
    PIP_IGNORE_INSTALLED=0 \
    HAILORT_LOGGER_PATH=NONE

# Install build dependencies and Python packages (setuptools and wheel)
RUN buildDeps="autoconf \
    automake \
    ca-certificates \
    cmake \
    g++ \
    gcc \
    git \
    make \
    zip \
    unzip" && \
    apt-get -yqq update && \
    apt-get install -yq --no-install-recommends ${buildDeps} \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel && \
    # Upgrade pip, setuptools, and wheel to the latest versions
    pip3 install --upgrade pip setuptools wheel

# Compile hailort from the source
RUN DIR=/tmp && mkdir -p ${DIR} && cd ${DIR} && \
    git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git && \
    cd hailort && \
    cmake -S. -Bbuild -DCMAKE_BUILD_TYPE=Release && cmake --build build --config release --target install

# Build Python wheel and sanitize metadata
RUN cd /tmp/hailort/hailort/libhailort/bindings/python/platform && \
    python3 setup.py bdist_wheel --dist-dir=/wheels && \
    pip3 wheel . -w /wheels && \
    # Sanitize produced wheels to remove any lingering 'license-file' metadata lines
    for whl in /wheels/*.whl; do \
        tmpdir=$(mktemp -d); \
        unzip -q "$whl" -d "$tmpdir"; \
        find "$tmpdir" -maxdepth 2 -type f -path '*/METADATA' -exec sed -i '/^license-file:/Id' {} +; \
        (cd "$tmpdir" && zip -qr "$whl.fixed" .); \
        mv "$whl.fixed" "$whl"; \
        rm -rf "$tmpdir"; \
    done && \
    ls -al /wheels/

# Stage 2: Final image with Python dependencies
FROM python:3.13-slim

ARG HAILO_VERSION
ARG DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies
RUN apt-get update && apt-get install -yq --no-install-recommends \
    ca-certificates \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Hailo runtime binaries and wheels from the build stage
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/hailortcli
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/libhailort.so.${HAILO_VERSION}
COPY --from=build /wheels /wheels/

# Install Python dependencies including the Hailo wheel and requirements.txt
COPY requirements.txt .
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    pip3 install /wheels/*.whl

# Copy application code
WORKDIR /app
COPY . .

EXPOSE 8000

# Start the application (use CMD for flexibility)
CMD ["python3", "run_api.py"]
