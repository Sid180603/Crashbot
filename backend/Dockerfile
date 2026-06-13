# ============================================
# PHASE 5: Backend Dockerfile with Multi-Platform Support
# Includes GDB and LLDB for Linux/macOS crash analysis
# ============================================

FROM python:3.12-slim as base

# Install system dependencies including debuggers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    gdb \
    lldb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/dumps /app/storage/symbols /app/storage/chroma_db /app/logs

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]


# ============================================
# Production stage (optional)
# ============================================
FROM base as production

ENV ENVIRONMENT=production
ENV DEBUG=false

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
