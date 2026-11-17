"""Backend configuration loaded from the environment."""

import os

from dotenv import load_dotenv

load_dotenv()


def frontend_origins() -> list[str]:
    """Return explicit browser origins allowed to call the API."""
    raw = os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise ValueError("FRONTEND_ORIGINS must contain explicit origins, not '*'.")
    return origins

