from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


def _load_backend_env():
    """Load backend/.env for standalone uvicorn runs without leaking secrets."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    import os

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_backend_env()

from stations.geocoding_service import geocode_query_with_meta  # noqa: E402


app = FastAPI(
    title="SmartFuel Search API",
    version="0.1.0",
    description="Read-only lightweight location search sidecar.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/search-api/health/")
def health():
    return {"status": "ok", "service": "search-api"}


@app.get("/search-api/locations/search/")
def search_locations(query: str = Query(..., min_length=1, max_length=120)):
    return geocode_query_with_meta(query)
