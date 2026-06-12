# SmartFuel API Contract Chunks

This directory contains endpoint-specific API contract chunks.

Use these chunks during implementation instead of loading the full `docs/02_api_blueprint.json`.

The full blueprint remains the canonical index, but day-to-day coding should use only the endpoint being implemented.

## Current Chunks

- `recommendations_quote.json`: `POST /api/v1/recommendations/quote/`
- `stations_nearby.json`: `GET /api/v1/stations/nearby/`
- `locations_geocode.json`: `GET /api/v1/stations/geocode/`
- `locations_reverse_geocode.json`: `GET /api/v1/stations/reverse-geocode/`
- `stations_refresh.json`: `POST /api/v1/stations/refresh/`
- `accounts_auth.json`: signup, login, logout, and current-user APIs
- `vehicles_profile.json`: default-vehicle `GET`/`PUT` plus vehicle list, create, update, delete, and set-default APIs
- `cards_policies.json`: manual card policy and Naver-based card discovery APIs
- `cards_catalog.json`: card catalog search and save-from-catalog APIs
- `cards_ingestion.json`: controlled Selenium card ingestion contract
- `stations_opinet.json`: Opinet synchronization boundary
