# QA Automation Framework - Main Dockerfile for Fly.io deployment
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    android-tools-adb \
    imagemagick \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/requirements.txt backend-requirements.txt
COPY bot/requirements.txt bot-requirements.txt
COPY infra/requirements.txt infra-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir \
    -r backend-requirements.txt \
    -r bot-requirements.txt \
    -r infra-requirements.txt

# Copy the entire application
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Make scripts executable
RUN chmod +x automation/scripts/*.sh automation/scripts/*.py
RUN chmod +x bot/*.py backend/*.py infra/*.py infra/*.sh

# Create log directories
RUN mkdir -p /var/log/qa-framework && \
    chown -R appuser:appuser /var/log/qa-framework

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 5000 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python3 -c "from utils.proxy import verify_proxy; verify_proxy()" || exit 1

# Default command runs the orchestrator
CMD ["python3", "bot/app.py"]