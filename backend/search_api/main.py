from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


import os
from dotenv import load_dotenv

def _load_backend_env():
    """Load backend/.env for standalone uvicorn runs without leaking secrets."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)

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
