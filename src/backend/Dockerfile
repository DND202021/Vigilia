# ERIOP Backend Dockerfile
# Simplified build for production

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "sqlalchemy>=2.0.25" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.0" \
    "redis>=5.0.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.6" \
    "httpx>=0.26.0" \
    "paho-mqtt>=1.6.1" \
    "structlog>=24.1.0" \
    "gunicorn>=21.0.0" \
    "email-validator>=2.0.0" \
    "psycopg2-binary>=2.9.0" \
    "bcrypt>=4.0.0" \
    "python-socketio>=5.10.0" \
    "pyotp>=2.9.0" \
    "qrcode[pil]>=7.4.0"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 eriop && \
    mkdir -p /app/logs && \
    chown -R eriop:eriop /app

USER eriop

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Railway uses PORT env var, default to 8000
ENV PORT=8000

# Use gunicorn with uvicorn workers for production
CMD python -m gunicorn app.main:app \
    --bind "0.0.0.0:$PORT" \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
