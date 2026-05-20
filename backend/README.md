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
- `POST /api/v1/recommendations/quote/`: quote recommendations. Anonymous users must send `vehicle.fuel_efficiency_kmpl`; authenticated users may rely on a saved vehicle profile.

## Data Boundaries

- Recommendation ranking and cost calculation stay in `stations/services.py`.
- `CardCatalog` rows collected from Selenium remain `unverified` and are not used for ranking until a user confirms them into `CardPolicy` or an admin verifies them.
- Card ingestion is run through management commands, not through the recommendation request path.

## Environment

- `OPINET_API_KEY`: required only for Opinet synchronization commands.
- `CARD_INGESTION_ALLOWED_DOMAINS`: comma-separated allowlist for card ingestion sources.

## Card Ingestion

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py ingest_card_search --limit 5 --scroll-count 2 --dry-run --browser-binary 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

## Local Verification

```powershell
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py test
```
