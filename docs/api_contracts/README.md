# SmartFuel API Contract Chunks

This directory contains endpoint-specific API contract chunks.

Use these chunks during implementation instead of loading the full `docs/02_api_blueprint.json`.

The full blueprint remains the canonical index, but day-to-day coding should use only the endpoint being implemented.

## Current Chunks

- `recommendations_quote.json`: `POST /api/v1/recommendations/quote/`
- `stations_nearby.json`: `GET /api/v1/stations/nearby/`
- `cards_policies.json`: manual card policy and Naver-based card discovery APIs
