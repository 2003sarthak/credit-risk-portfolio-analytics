"""FastAPI application foundation."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import frontend_origins

app = FastAPI(title="Credit Risk Portfolio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}

