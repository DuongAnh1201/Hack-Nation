import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Physics Study API")

origins_raw = os.getenv("FRONTEND_ORIGINS", "*")
if origins_raw.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True if allow_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Used by Render health checks and the CD smoke test."""
    return {"status": "ok"}


# Routers from app/api/ get registered here.
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api.lab import router as lab_router  # noqa: E402
from app.api.live import router as live_router  # noqa: E402

app.include_router(lab_router)
app.include_router(live_router)

# Serve the website from the same address, so a live demo needs one URL and no CORS setup
# (http://localhost:8000/). Mounted last: /health and /api/* above take precedence.
SITE = Path(__file__).resolve().parents[2] / "frontend"
if (SITE / "index.html").is_file():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
