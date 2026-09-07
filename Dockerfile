FROM python:3.11-slim

# Install system dependencies: ADB, FFmpeg, and build libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    adb \
    ffmpeg \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Storage mounts
VOLUME ["/app/captures", "/app/data"]

EXPOSE 8765

# Run continuous sentinel daemon by default
CMD ["python", "main.py", "daemon"]
