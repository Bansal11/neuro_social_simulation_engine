"""
Production entry point for the Docker container.

Mounts the FastAPI backend and serves the pre-built Vite frontend as static
files. In production the Vite dev-server proxy is replaced by this single
process — the browser loads the SPA from ``/``, and API/WebSocket calls go
to ``/api/*`` and ``/ws/*`` on the same origin.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Backend source lives in /app/backend — add it to sys.path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from main import app  # noqa: E402  — must come after sys.path manipulation

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Health endpoint (used by Docker HEALTHCHECK and cloud load balancers)
# ---------------------------------------------------------------------------

@app.get("/api/v1/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Serve frontend static assets
# ---------------------------------------------------------------------------

if FRONTEND_DIR.is_dir():
    # Serve static assets (JS, CSS, images) under /assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    # Catch-all: serve index.html for any non-API route (SPA client-side routing)
    @app.get("/{full_path:path}", tags=["frontend"])
    async def serve_spa(full_path: str) -> FileResponse:
        """Return index.html for all non-API paths (SPA fallback)."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        ws_max_size=16 * 1024 * 1024,  # 16 MB — generous for tick payloads
    )
