FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and proxy utilities
COPY app.py .

# Copy proxy utilities if available
COPY utils/proxy.py ./utils/ 2>/dev/null || echo "Proxy utils not found, using fallback"
RUN mkdir -p utils && touch utils/__init__.py

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Environment variables for proxy
ENV SMARTPROXY_USER=${SMARTPROXY_USER}
ENV SMARTPROXY_PASS=${SMARTPROXY_PASS}
ENV SMARTPROXY_HOST=${SMARTPROXY_HOST}
ENV SMARTPROXY_PORT=${SMARTPROXY_PORT}

# Health check with proxy verification
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]