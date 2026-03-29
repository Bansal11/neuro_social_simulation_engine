# =============================================================================
# Multi-stage Dockerfile for the Neuro-Social Simulation Engine
#
# Stage 1 (frontend-build): Builds the React/Vite frontend into static assets.
# Stage 2 (runtime):        Runs the FastAPI backend and serves the frontend
#                            static files via Starlette StaticFiles mount.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Build frontend
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Prevent .pyc files and enable unbuffered stdout/stderr for container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (none required beyond slim base, but leave hook for numpy)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir -e "./backend[dev]" 2>/dev/null || true
# Full install after copying source
COPY backend/ ./backend/
RUN pip install --no-cache-dir -e "./backend"

# Copy built frontend assets from Stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy the static file serving wrapper
COPY docker/serve.py ./serve.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "serve.py"]
