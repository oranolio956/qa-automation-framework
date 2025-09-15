FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and proxy utilities
COPY schemas.py .
COPY app.py .

# Copy Bright Data proxy utilities if available
COPY utils/brightdata_proxy.py ./utils/ 2>/dev/null || echo "Bright Data proxy utils not found, using fallback"
RUN mkdir -p utils && touch utils/__init__.py

# Create necessary directories
RUN mkdir -p /var/log/qa-framework && \
    chown -R appuser:appuser /app /var/log/qa-framework

# Environment variables for Bright Data proxy
ENV BRIGHTDATA_ZONE_KEY=${BRIGHTDATA_ZONE_KEY}
ENV BRIGHTDATA_ENDPOINT=${BRIGHTDATA_ENDPOINT}

# Health check with Bright Data proxy verification
HEALTHCHECK --interval=1m --timeout=10s --retries=3 \
    CMD python3 -c "from utils.brightdata_proxy import verify_proxy; verify_proxy(); print('BrightData proxy OK')" || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "app.py"]