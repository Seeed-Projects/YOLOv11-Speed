ARG BUILD_FROM=ubuntu:20.04
FROM ${BUILD_FROM} as build

ARG HAILO_VERSION
ARG MAKEFLAGS="-j2"

ENV \
    DEBIAN_FRONTEND=noninteractive \
    PIP_IGNORE_INSTALLED=0 \
    HAILORT_LOGGER_PATH=NONE

RUN \
    buildDeps="autoconf \
    automake \
    ca-certificates \
    cmake \
    g++ \
    gcc \
    git \
    make \
    zip \
    unzip \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel" && \
    apt-get -yqq update && \
    apt-get install -yq --no-install-recommends ${buildDeps}

# Compile hailort
RUN \
    DIR=/tmp && mkdir -p ${DIR} && cd ${DIR} && \
    git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git && \
    cd hailort && \
    cmake -S. -Bbuild -DCMAKE_BUILD_TYPE=Release && cmake --build build --config release --target install

# Build and create wheel
RUN \
    cd /tmp/hailort/hailort/libhailort/bindings/python/platform && \
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

# Copy application files and install dependencies
FROM ${BUILD_FROM}

ARG HAILO_VERSION
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -yq --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    ca-certificates \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy hailort binaries and libraries from the build stage
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/hailortcli
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/libhailort.so.${HAILO_VERSION}
COPY --from=build /wheels /wheels/

# Install Python dependencies including the Hailo wheel
COPY requirements.txt .
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    pip3 install /wheels/*.whl

# Copy application code
WORKDIR /app
COPY . .

EXPOSE 8000

CMD ["python3", "run_api.py"]