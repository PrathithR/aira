# ============================================================
# AIRA - AI-Powered Responsive Assistant
# Production Dockerfile
# ============================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /aira

# Install Python dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy project source
COPY . .

# Create non-root user and hand over ownership
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser \
    && mkdir -p /aira/data \
    && chown -R appuser:appuser /aira

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production CMD — no --reload, single worker for Phase 0
# Dev compose overrides this with --reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
