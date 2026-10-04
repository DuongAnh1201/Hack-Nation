import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Physics Study API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Used by Render health checks and the CD smoke test."""
    return {"status": "ok"}


# Routers from app/api/ get registered here.
from app.api.lab import router as lab_router  # noqa: E402

app.include_router(lab_router)
