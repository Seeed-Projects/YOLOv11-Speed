# Use an official Python runtime as a parent image
# Note: For Hailo hardware support, you may need to use a base image with Hailo drivers pre-installed
# or install the HailoRT package during the build process
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/app/.env

# Install system dependencies required for OpenCV and Hailo
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    pkg-config \
    libglib2.0-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment with system site packages
RUN python -m venv $VIRTUAL_ENV --system-site-packages

# Make sure we use the virtual environment
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install HailoRT Python package (version 4.22.0 as mentioned in README)
# This assumes you have access to the HailoRT wheel file
# You may need to download the appropriate wheel file for your target architecture
# RUN pip install hailort==4.22.0

# Copy the application code to the container
WORKDIR /app
COPY . /app

# Create output directory for results
RUN mkdir -p /app/output

# Create a dedicated user for running the application
RUN groupadd -r yolouser && useradd -r -g yolouser yolouser
RUN chown -R yolouser:yolouser /app
USER yolouser

# Make the run script executable
RUN chmod +x /app/run_detection.py

# Set the entrypoint to the run script
ENTRYPOINT ["python", "/app/run_detection.py"]

# Default command (can be overridden)
CMD ["--help"]