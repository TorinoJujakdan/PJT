# SmartFuel Backend

Django REST Framework backend for SmartFuel.

Expected apps:

- `core`: project configuration
- `accounts`: authentication and user profile
- `vehicles`: vehicle fuel efficiency
- `cards`: card discount policies
- `stations`: station data, fuel prices, recommendation service

The recommendation service contract is defined in `docs/03_recommendation_algorithm.md`.

## API Surface

- `POST /api/v1/accounts/signup/`: create a user and start a session.
- `POST /api/v1/accounts/login/`: log in with username and password.
- `POST /api/v1/accounts/logout/`: end the current session.
- `GET /api/v1/accounts/me/`: return login state and current user.
- `PATCH /api/v1/accounts/me/`: update username or email.
- `GET /api/v1/me/vehicle/`: fetch the authenticated user's default vehicle.
- `PUT /api/v1/me/vehicle/`: create or update the default vehicle.
- `GET /api/v1/me/cards/`: list the authenticated user's active card policies.
- `POST /api/v1/me/cards/`: create a manual card policy.
- `PATCH /api/v1/me/cards/{card_id}/`: update an owned active card policy.
- `DELETE /api/v1/me/cards/{card_id}/`: soft-delete an owned active card policy.
- `GET /api/v1/cards/catalog/`: search collected card catalog candidates.
- `POST /api/v1/me/cards/from-catalog/`: save a catalog candidate as a user-confirmed card policy.
- `GET /api/v1/stations/nearby/`: list nearby stations for a fuel type.
- `GET /api/v1/stations/geocode/`: geocode an address or place query through the backend Naver proxy.
- `GET /api/v1/stations/reverse-geocode/`: resolve a selected coordinate to an address label.
- `POST /api/v1/stations/refresh/`: hydrate nearby station prices from Opinet for a selected coordinate.
- `POST /api/v1/recommendations/quote/`: quote recommendations. Anonymous users must send `vehicle.fuel_efficiency_kmpl`; authenticated users may rely on a saved vehicle profile.

## Lightweight Search Sidecar

The optional FastAPI sidecar handles read-only detailed location search while the
Django geocode endpoint remains the compatibility fallback.

- `GET /search-api/health/`: sidecar health check.
- `GET /search-api/locations/search/?query=...`: normalized address/place
  results using the same Naver Geocoding + Naver Local Search service as Django.

Local run commands:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
..\.venv\Scripts\uvicorn.exe search_api.main:app --host 127.0.0.1 --port 8001 --reload
```

## Data Boundaries

- Recommendation ranking and cost calculation stay in `stations/services.py`.
- `CardCatalog` rows collected from Selenium remain `unverified` and are not used for ranking until a user confirms them into `CardPolicy` or an admin verifies them.
- Card ingestion is run through management commands, not through the recommendation request path.

## Environment

- `OPINET_API_KEY`: required only for Opinet synchronization commands.
- `NAVER_GEOCODING_CLIENT_ID` / `NAVER_GEOCODING_CLIENT_SECRET`: server-side Naver Geocoding and Reverse Geocoding credentials. Legacy `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` are still accepted.
- `NAVER_LOCAL_CLIENT_ID` / `NAVER_LOCAL_CLIENT_SECRET`: optional server-side Naver Local Search credentials for detailed business/building search. `NAVER_SEARCH_*` and `NAVER_OPENAPI_*` aliases are also accepted. Legacy `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` are still accepted, but Naver Cloud Maps keys and Naver Developers Search keys are separate credential families.
- `CARD_INGESTION_ALLOWED_DOMAINS`: comma-separated allowlist for card ingestion sources.

## Card Ingestion

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py ingest_card_search --limit 5 --scroll-count 2 --dry-run --browser-binary 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

## Local Verification

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py test
```
