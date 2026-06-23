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
- `GET /api/v1/me/vehicles/`: list all vehicles owned by the authenticated user.
- `POST /api/v1/me/vehicles/`: create an owned vehicle.
- `PATCH`/`PUT /api/v1/me/vehicles/{vehicle_id}/`: update an owned vehicle.
- `DELETE /api/v1/me/vehicles/{vehicle_id}/`: delete an owned vehicle and promote a remaining vehicle when the default is deleted.
- `POST /api/v1/me/vehicles/{vehicle_id}/set-default/`: make an owned vehicle the default.
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
- `GET /api/v1/community/posts/`: list and search public community posts.
- `POST /api/v1/community/posts/`: create a community post with title, content, and optional tags.
- `GET`/`PATCH`/`DELETE /api/v1/community/posts/{post_id}/`: read, update, or delete a community post.
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
- Vehicle names are required, trimmed, non-unique, and limited to 40 characters. `vehicle_type` accepts only `sedan`, `suv`, `rv_mpv`, `sports_coupe`, `hatchback`, `wagon`, `convertible`, `pickup`, or `micro_city`.
- Migration `vehicles.0003_reset_profiles_add_name_vehicle_type` deletes only `VehicleProfile` rows. User accounts, cards, stations, and fuel-price rows are preserved.
- Migration `vehicles.0004_vehicleprofile_vehicles_one_default_per_user` enforces one default vehicle at most per user; clients change it through the set-default endpoint.
- Migration `vehicles.0005_reset_profiles_expand_vehicle_types` intentionally deletes existing vehicle profiles and replaces the five-type choices metadata with the nine-type contract.
- `CardCatalog` rows collected from Selenium remain `unverified` and are not used for ranking until a user confirms them into `CardPolicy` or an admin verifies them.
- Card ingestion is run through management commands, not through the recommendation request path.
- Selenium card ingestion downloads public card artwork into `MEDIA_ROOT/card_images/` and stores the file path plus a normalized JSON payload on `CardCatalog`; remote image URLs are retained only as source provenance.

## Environment

- `OPINET_API_KEY`: required only for Opinet synchronization commands.
- `NAVER_GEOCODING_CLIENT_ID` / `NAVER_GEOCODING_CLIENT_SECRET`: server-side Naver Cloud Maps credentials shared by Geocoding, Reverse Geocoding, and Directions. Legacy `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` remain accepted for these Maps APIs.
- `NAVER_LOCAL_CLIENT_ID` / `NAVER_LOCAL_CLIENT_SECRET`: optional NAVER Developers Search credentials for registered businesses, buildings, and landmarks. `NAVER_SEARCH_*` and `NAVER_OPENAPI_*` aliases are also accepted. Cloud Maps `NAVER_CLIENT_*` credentials are intentionally not used for Local Search.
- `CARD_INGESTION_ALLOWED_DOMAINS`: comma-separated allowlist for card ingestion sources.

## 초기 데이터 설정 (Initial Data Setup)

Migration 적용 후 카드 카탈로그 데이터를 DB에 로드해야 합니다.  
`fixtures/card_data.json` 파일은 자동으로 반영되지 않으므로 아래 명령어를 **반드시 한 번 실행**해야 카드 검색이 정상적으로 동작합니다.

```powershell
cd backend
..\\.venv\\Scripts\\python.exe manage.py migrate
..\\.venv\\Scripts\\python.exe manage.py loaddata cards/fixtures/card_data.json
```

> **주의**: `loaddata`를 실행하지 않으면 카드 검색 결과가 빈 값으로 나옵니다.

로드 완료 후 아래 명령어로 데이터가 정상 입력되었는지 확인할 수 있습니다:

```powershell
..\\.venv\\Scripts\\python.exe manage.py shell -c "from cards.models import CardCatalog; print('CardCatalog:', CardCatalog.objects.count())"
```

정상이라면 `CardCatalog: 152` 와 같이 출력됩니다.

---

## Card Ingestion

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py ingest_card_search --limit 5 --scroll-count 2 --dry-run --browser-binary 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

## Local Verification

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py test
```
