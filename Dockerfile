# ═════════════════════════════════════════════════════════════════════════════
# Stage 1: Build & Dependency Compilation Stage
# ═════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to a clean prefix
COPY backend/requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# ═════════════════════════════════════════════════════════════════════════════
# Stage 2: Hardened Production Runtime Stage
# ═════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=production

WORKDIR /app

# Install minimal runtime dependencies (curl for healthchecks, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Security: Create dedicated non-root user and group
RUN groupadd -g 10001 mailmind && \
    useradd -u 10001 -g mailmind -s /bin/bash -m mailmind

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy backend application code
COPY backend/ /app/backend/

# Set ownership to non-root user
RUN chown -R mailmind:mailmind /app

# Switch to security non-root user execution
USER mailmind:mailmind

EXPOSE 8000

# Production Health Check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/livez || exit 1

# Launch production server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
