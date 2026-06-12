# SmartFuel QA Report Log

This file records validation results for the recommendation algorithm and API contract.

## Initial Contract QA Scenarios

Status: pending implementation

1. Cheapest station is recommended when there is no card discount.
2. A higher-price station is recommended when card discount makes the effective total cost lower.
3. A distant discounted station is not recommended when travel cost is larger than the discount benefit.
4. Anonymous recommendation without vehicle efficiency returns `MISSING_VEHICLE_EFFICIENCY`.
5. Logged-in recommendation uses the saved vehicle fuel efficiency when request vehicle input is omitted.
6. Invalid latitude or longitude returns `INVALID_LOCATION`.
7. Unsupported fuel type returns `UNSUPPORTED_FUEL_TYPE`.
8. No station inside the search radius returns `NO_STATION_CANDIDATE`.

## Slice 1 Backend QA

Date: 2026-05-18

Scope:

- Django project scaffold
- `GasStation` and `FuelPrice` models
- dummy station data loader
- `GET /api/v1/stations/nearby/`
- bounding box and Haversine candidate search

Verification:

- `manage.py check`: passed
- `manage.py migrate`: passed
- `manage.py load_dummy_stations`: loaded 4 stations and 8 fuel prices
- `manage.py test stations`: 5 tests passed

Covered cases:

1. Nearby gasoline stations return candidate list and metadata.
2. Invalid latitude returns `INVALID_LOCATION`.
3. Unsupported fuel type returns `UNSUPPORTED_FUEL_TYPE`.
4. Radius greater than 30km returns `INVALID_RADIUS`.
5. No station inside radius returns `NO_STATION_CANDIDATE`.

## Slice 2 Backend QA

Date: 2026-05-18

Scope:

- fuel-price-only recommendation
- `POST /api/v1/recommendations/quote/`
- `target_liters * fuel_price_per_liter` refuel cost calculation
- ranking by `effective_total_cost`, then distance, fuel price, station id
- vehicle, travel cost, and card discount intentionally excluded

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test stations`: 9 tests passed
- API smoke test for `POST /api/v1/recommendations/quote/`: returned 200

Covered cases:

1. Fuel-price-only recommendation selects the lowest refuel cost station.
2. Response includes `recommendation`, `baseline`, `candidates`, and `meta`.
3. `include_candidates=false` returns an empty candidate list while preserving the recommendation.
4. Invalid target liters returns `INVALID_TARGET_LITERS`.
5. Unsupported fuel type returns `UNSUPPORTED_FUEL_TYPE`.

## Slice 3 Backend QA

Date: 2026-05-18

Scope:

- vehicle fuel-efficiency input validation
- round-trip travel cost calculation
- `effective_total_cost = refuel_cost + travel_cost`
- ranking by effective total cost, then distance, fuel price, station id
- card discount intentionally excluded

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test stations`: 10 tests passed
- API smoke test for `POST /api/v1/recommendations/quote/`: returned 200

Covered cases:

1. Travel cost changes the recommendation from the cheapest distant station to a lower effective-cost nearby station.
2. Response includes non-zero `travel_cost`.
3. Missing vehicle efficiency returns `MISSING_VEHICLE_EFFICIENCY`.
4. Existing Slice 1 nearby station tests still pass.
5. Existing Slice 2 target liters and fuel type error tests still pass.

## Slice 4 Pending QA Scenarios

Status: partially implemented

Scope:

- manual card benefit input
- Naver-based card benefit discovery
- card image display fields
- card discount calculation
- enhanced recommendation reason

Required cases:

1. User-created manual card policy can be used for recommendation.
2. Naver-discovered policy is returned as `unverified` and is not used in recommendation ranking.
3. User-confirmed discovered policy can be used in recommendation ranking.
4. Card image URL is included in selected card response when available.
5. Missing card image falls back to frontend placeholder behavior.
6. Selected card reason includes issuer, card name, discount amount, travel cost, and final effective total cost.
7. A more expensive station wins when confirmed card discount offsets the price and travel cost.
8. A discounted but distant station loses when travel cost is larger than the discount benefit.

## Slice 4 Card Policy API QA

Date: 2026-05-19

Scope:

- `cards` Django app
- `CardPolicy` model
- `CardBenefitSource` model
- manual card policy create/list/delete APIs
- Naver discovery API service boundary
- card image URL field
- source and verification status fields

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test cards`: 7 tests passed
- `manage.py test stations`: 10 tests passed
- `manage.py migrate`: passed
- API smoke test for `POST /api/v1/me/cards/`: returned 201
- API smoke test for `GET /api/v1/me/cards/`: returned 200
- API smoke test for `GET /api/v1/cards/discovery/`: returned 200 with `provider_status=not_configured`

Covered cases:

1. Card policy APIs require authentication.
2. User-created manual card policy is stored as `source_type=manual`.
3. Manual card policy is stored as `verification_status=user_confirmed`.
4. Card image URL is accepted and returned.
5. Users only see their own active card policies.
6. Delete API soft-deletes the card policy.
7. Missing card policy delete returns `CARD_POLICY_NOT_FOUND`.
8. Naver discovery endpoint safely falls back when credentials are missing.
9. Invalid percentage discount over 100 returns `INVALID_CARD_POLICY`.

Slice 4 recommendation ranking work completed below:

1. Apply confirmed card policies to recommendation ranking.
2. Exclude unverified Naver discovery candidates from recommendation ranking.
3. Include selected card payload in recommendation responses.
4. Strengthen recommendation reason with card discount details.

## Slice 4 Recommendation Ranking QA

Date: 2026-05-19

Scope:

- Apply eligible card policies to recommendation ranking
- Exclude unverified Naver-discovered card policies from ranking
- Include selected card payload in recommendation responses
- Include card discount, travel cost, and final cost in recommendation reason
- Keep baseline as the best no-card effective cost

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test stations`: 13 tests passed
- `manage.py test cards`: 7 tests passed
- `manage.py test`: 20 tests passed

Covered cases:

1. User-created saved card policy can change recommendation ranking.
2. Selected card response includes card name, issuer, image URL, source type, verification status, and calculated discount.
3. Recommendation reason includes selected card name, card discount amount, travel cost, and final expected cost.
4. Unverified Naver-discovered policy is ignored for recommendation ranking.
5. User-confirmed Naver-discovered policy can affect recommendation ranking.
6. Existing no-card recommendation still returns `selected_card=null` and `card_discount_amount=0`.
7. Existing station search, target liters, fuel type, and vehicle efficiency error tests still pass.

Remaining Slice 4 risk:

1. Frontend card image placeholder behavior is not covered yet because Slice 7 frontend work has not started.
2. Route-distance or issuer-authoritative card data integrations remain outside the local MVP scope.

## Slice 5 Ranking and Rounding QA

Date: 2026-05-19

Scope:

- Final `effective_total_cost` ranking order
- Ranking tiebreaker order through station id
- API response rounding for target liters, distance, and KRW costs
- Regression check after Slice 4 card ranking changes

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test stations`: 15 tests passed
- `manage.py test cards`: 7 tests passed
- `manage.py test`: 22 tests passed

Covered cases:

1. Candidates are returned in final ranking order.
2. Equal effective cost, distance, and fuel price fall back to ascending `station_id`.
3. `target_liters` is rounded to 2 decimal places in the response.
4. KRW cost fields are returned as integers.
5. Station distance remains rounded to 2 decimal places.
6. Slice 4 confirmed-card and unverified-card behavior still passes.

## Slice 6 Recommendation Explanation QA

Date: 2026-05-19

Scope:

- recommendation `reason` field
- selected card details in recommendation response
- explanation coverage for fuel price, card discount, travel cost, final cost, saving, and comparison reason
- no frontend work

Verification:

- `py_compile` for changed backend files: passed
- `manage.py check`: passed
- `manage.py test stations`: 16 tests passed
- `manage.py test cards`: 7 tests passed
- API smoke test for `POST /api/v1/recommendations/quote/`: returned 200

Covered cases:

1. Recommendation reason includes base fuel price and refuel cost.
2. Recommendation reason includes selected card issuer and card name when a card is applied.
3. Recommendation reason includes calculated card discount amount.
4. Recommendation reason includes travel cost.
5. Recommendation reason includes final effective total cost.
6. Recommendation reason includes estimated saving against baseline.
7. Recommendation reason includes comparison against cheaper or closer alternatives.
8. Selected card response keeps `card_image_url`.

## Slice 7 Frontend Recommendation Display QA

Date: 2026-05-19

Scope:

- Vue 3 + Vite frontend scaffold
- recommendation API client
- recommendation store
- `RecommendView.vue`
- location input
- fuel target input
- recommendation result display
- cost breakdown
- selected card image fallback area
- candidate comparison list

Verification:

- `npm.cmd install`: passed
- `npm.cmd run build`: passed
- Django dev server health check: passed
- Vite dev server health check: passed
- Browser smoke test for `http://127.0.0.1:5173`: passed
- Browser click test for `추천 받기`: passed

Covered cases:

1. Initial screen renders location and fuel controls.
2. User can request a recommendation from the frontend.
3. Frontend displays backend `recommendation.station` without recalculating ranking.
4. Frontend displays refuel cost, card discount, travel cost, and effective total cost.
5. Frontend displays backend-provided recommendation reason.
6. Frontend displays backend-sorted candidate list.
7. Frontend handles selected-card image URL or fallback card icon.

Browser screenshot:

```text
frontend/slice7-browser-check.png
```

## Phase 3 Inspection QA

Date: 2026-05-19

Scope:

- Backend unit/API tests
- Frontend production build verification
- Recommendation scenario QA against the required scenarios
- Docker smoke test readiness check

Verification:

- `manage.py check`: passed
- `manage.py test`: 25 tests passed
- `npm.cmd run build`: passed
- Docker CLI availability check: passed
- Docker Compose availability check: passed
- Docker smoke test: blocked because `docker-compose.yml`, `Dockerfile.backend`, and `Dockerfile.frontend` are not present yet

Covered QA scenarios:

1. Cheapest/lowest effective-cost station is recommended when no card exists.
2. A more expensive station is recommended when a confirmed card discount makes it cheaper.
3. A discounted distant station is rejected when travel cost removes the benefit.
4. No candidate station returns `NO_STATION_CANDIDATE`.
5. Missing vehicle efficiency returns `MISSING_VEHICLE_EFFICIENCY`.
6. Invalid location returns `INVALID_LOCATION`.
7. Unsupported fuel type returns `UNSUPPORTED_FUEL_TYPE`.

Phase 3 changes:

1. Added recommendation API regression coverage for `NO_STATION_CANDIDATE`.
2. Added recommendation API regression coverage for a distant discounted station losing because travel cost exceeds the benefit.

Remaining Phase 3 risk:

1. Docker smoke test cannot be executed until Phase 4 Docker artifacts are added.

## Refactor Feature Spec v1.1 QA

Date: 2026-05-19

Scope:

- `accounts` app with signup, login, logout, current-user, and profile patch APIs
- `vehicles` app with default vehicle profile model and `GET`/`PUT /api/v1/me/vehicle/`
- recommendation API saved-vehicle fallback for authenticated users
- automatic inclusion of authenticated users' active card policies
- card policy `PATCH` API
- Vue account, profile, vehicle, card, and recommendation flows
- split API contract chunks for accounts and vehicles

Verification:

- `manage.py test`: 34 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Signup starts a session and current-user lookup returns the new user.
2. Login and logout update session state.
3. Profile patch requires authentication.
4. Vehicle profile API requires authentication.
5. Vehicle `PUT` creates and updates the default profile without duplicating it.
6. Invalid vehicle efficiency returns `INVALID_VEHICLE_PROFILE`.
7. Authenticated recommendation can omit request `vehicle` when a saved profile exists.
8. Request `vehicle` overrides saved profile values.
9. Anonymous recommendation without vehicle still returns `MISSING_VEHICLE_EFFICIENCY`.
10. Card policy `PATCH` updates only an owned active policy.
11. Frontend production build succeeds after auth, vehicle, card, and recommendation flow changes.

## Refactor Feature Spec v1.2 Slice 1 QA

Date: 2026-05-19

Scope:

- CSRF bootstrap contract for `GET /api/v1/accounts/me/`
- Backend CSRF cookie guarantee for session-authenticated unsafe requests
- Frontend API client CSRF header handling
- Vehicle and card save-flow validation and user-facing status feedback

Verification:

- `manage.py test accounts vehicles cards`: 15 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. `GET /api/v1/accounts/me/` sets a `csrftoken` cookie for the browser.
2. Frontend unsafe API requests bootstrap CSRF when the cookie is missing.
3. Vehicle save UI validates required fuel type and `1.0` to `50.0` km/L efficiency before sending.
4. Card save UI validates required issuer/card name, non-negative discount value, and percentage discount maximum.
5. Card delete UI exposes pending/error state and refreshes the list after success.

Remaining risk:

1. Browser-level CSRF smoke test should be run after the local dev server is active.
2. App-wide Korean copy and navigation UX still need the later v1.2 UI slice.

## Refactor Feature Spec v1.2 Ingestion Config QA

Date: 2026-05-19

Scope:

- Replace card discovery's Naver Search API stub with controlled Selenium ingestion boundary
- Add card ingestion API contract
- Add Opinet backend API key loading boundary
- Add Opinet synchronization management command skeleton

Verification:

- `manage.py test cards stations.tests_opinet`: 12 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Card discovery no longer reads `NAVER_CLIENT_ID` or `NAVER_CLIENT_SECRET`.
2. Card discovery returns `source_type=selenium`.
3. Card discovery requires `CARD_INGESTION_ALLOWED_DOMAINS` before accepting a domain.
4. Domains outside the allowlist return `domain_not_allowed`.
5. Opinet synchronization requires `OPINET_API_KEY` in the backend process environment.
6. Recommendation requests remain decoupled from external Opinet calls.

Environment variables:

```text
CARD_INGESTION_ALLOWED_DOMAINS=example-card-domain.com,another-domain.com
OPINET_API_KEY=issued-opinet-api-key
```

Default approved card ingestion domain:

```text
https://card-search.naver.com/list?companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC
```

Remaining risk:

1. Real Selenium parsing is not implemented until the user provides approved card benefit domains.
2. Real Opinet request/response mapping is not implemented until the exact Opinet endpoint contract is selected.

## Refactor Feature Spec v1.2 Selenium Card Search Slice QA

Date: 2026-05-19

Scope:

- Add `CardCatalog` as an unverified card benefit candidate store
- Add Selenium dependency declaration
- Add allowlisted Selenium card search service boundary
- Add `ingest_card_search` management command
- Keep card ingestion outside recommendation request handling

Approved source:

```text
https://card-search.naver.com/list?companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC
```

Verification:

- `manage.py test cards`: 14 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. `card-search.naver.com` is accepted as the approved Selenium source domain.
2. Unknown domains are rejected before collection.
3. Scraped candidates are saved as `source_type=selenium`.
4. Scraped candidates are saved as `verification_status=unverified`.
5. Re-ingesting the same `source_url` updates the existing catalog row instead of duplicating it.

Remaining risk:

1. The real browser collection command requires installing `selenium` from `backend/requirements.txt`.
2. Chrome/ChromeDriver availability must be verified in the local execution environment before running the live collection command.
3. The generic DOM extraction may need selector tuning after inspecting the live Naver card search page structure.

## Refactor Feature Spec v1.2 Naver Card Parser Slice QA

Date: 2026-05-19

Scope:

- Inspect the approved Naver card search page structure
- Tune Selenium extraction for Naver card search text flow
- Parse card name, inferred issuer, discount type, and discount value from search results

Observed source structure:

- The approved page exposes a card result flow of card name, primary benefit, annual fee/tags.
- Examples observed include `KB국민 굿데이카드` with `주유소/충전소 리터당 60원 청구할인`, `삼성 iD SELECT ALL 카드` with `주유 7% 할인`, and `디지로카 London` with `주유비 최대 1.7% 캐시백`.

Verification:

- `manage.py test cards`: 16 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Text extraction ignores page headings such as `신용카드 136`.
2. `리터당 60원` is parsed as `per_liter` discount value `60`.
3. `7%` and `1.7%` are parsed as `percentage` discount values.
4. Common Korean card issuer names are inferred from card names.
5. Parsed candidates still save as `source_type=selenium` and `verification_status=unverified`.

Remaining risk:

1. Live Selenium execution may still require selector tuning for image URLs and detail links after Chrome/ChromeDriver is confirmed locally.
2. Some cards may describe benefits in non-standard wording and need additional parser rules.

## Refactor Feature Spec v1.2 Live Selenium Ingestion QA

Date: 2026-05-19

Scope:

- Install Selenium dependency into the active backend Python runtime
- Apply `cards.0002_cardcatalog_and_more` migration
- Run the approved Naver card search Selenium ingestion dry-run
- Save extracted candidates into `CardCatalog`

Environment:

- Chrome binary: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Approved source: `https://card-search.naver.com/list?companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC`

Live ingestion result:

- Dry-run extracted 9 fuel-related card candidates.
- Saved 9 `CardCatalog` rows.
- All saved rows use `verification_status=unverified`.

Saved candidates:

1. `LOCA LIKIT 1.2` - `percentage 1.20`
2. `삼성 iD SELECT ALL 카드` - `percentage 7.00`
3. `신한카드 Deep Oil` - `percentage 10.00`
4. `삼성카드 taptap S` - `fixed_amount 2000.00`
5. `KB국민 굿데이카드` - `per_liter 60.00`
6. `삼성 iD PLUG-IN 카드` - `percentage 20.00`
7. `디지로카 London` - `percentage 1.70`
8. `삼성 iD GLOBAL 카드` - `percentage 1.00`
9. `신한카드 Mr.Life` - `percentage 10.00`

Verification:

- `manage.py test cards`: 16 tests passed
- `npm.cmd run build`: passed

Remaining risk:

1. Extracted candidates are intentionally unverified and must not affect recommendation ranking until user confirmation or admin verification exists.
2. Image URL and detail URL extraction still need a follow-up selector-specific tuning slice.

## Refactor Feature Spec v1.2 Card Catalog Confirmation Slice QA

Date: 2026-05-19

Scope:

- Add card catalog search API
- Add create-my-card-from-catalog API
- Add frontend card catalog search panel
- Add one-click confirmation from catalog candidate into user-owned `CardPolicy`

API changes:

- `GET /api/v1/cards/catalog/`
- `POST /api/v1/me/cards/from-catalog/`

Verification:

- `manage.py test cards stations`: 42 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Authenticated users can search `CardCatalog` candidates by card name.
2. Catalog results can include unverified Selenium candidates without becoming user cards.
3. Authenticated users can explicitly save a catalog candidate into their own `CardPolicy`.
4. Created policies from catalog use `source_type=selenium`.
5. Created policies from catalog use `verification_status=user_confirmed`.
6. Missing catalog IDs return `CARD_CATALOG_NOT_FOUND`.
7. Frontend card management screen can search catalog candidates and save a selected candidate.

Remaining risk:

1. Catalog candidate edit-before-save UX is not implemented yet.
2. Catalog image/detail link extraction still depends on the next selector-specific Selenium tuning slice.

## Refactor Feature Spec v1.2 Card Catalog Edit And Selector Slice QA

Date: 2026-05-19

Scope:

- Allow users to edit catalog candidate benefit fields before saving
- Preserve explicit user confirmation before `CardPolicy` creation
- Tune Selenium selectors for Naver card search item rows
- Update existing fallback catalog rows with real detail URLs and image URLs

API changes:

- `POST /api/v1/me/cards/from-catalog/` now accepts optional override fields:
  - `discount_type`
  - `discount_value`
  - `brand_scope`
  - `min_payment_amount`
  - `max_discount_amount`
  - `monthly_discount_limit`
  - `monthly_remaining_discount`
  - `user_memo`

Live ingestion result:

- Re-ingestion saved 9 unverified catalog candidates.
- Existing fallback `#candidate-*` rows were updated by card name.
- All 9 rows now have Naver detail URLs.
- All 9 rows now have card image URLs.
- Candidate confidence updated to `0.85` when both detail URL and image URL are present.

Verification:

- `manage.py test cards`: 23 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Users can override discount and limit fields before saving catalog candidates.
2. Invalid percentage overrides above 100 are rejected.
3. Frontend opens a confirmation/edit panel before saving catalog candidates.
4. Naver `li.item` selector extracts `.name`, `.desc`, `img.img`, and `a.anchor[href]`.
5. Re-ingestion updates existing catalog rows when source URLs improve.

Remaining risk:

1. Brand-specific parsing is still coarse and defaults to `all`.
2. Annual fee and exact issuer metadata remain best-effort inferred values.

## Refactor Feature Spec v1.2 Card Detail Parsing Slice QA

Date: 2026-05-20

Scope:

- Extend the card ingestion contract for detail-page parsing fields
- Add optional `--detail` enrichment to `ingest_card_search`
- Parse public detail text for brand scope, minimum payment, per-transaction cap, monthly limit, raw summary, and confidence
- Keep enriched data in `CardCatalog` only, with `verification_status=unverified`
- Preserve user confirmation as the only path from `CardCatalog` into `CardPolicy`

API/command contract changes:

- `CardCatalog` response explicitly includes:
  - `brand_scope`
  - `min_payment_amount`
  - `max_discount_amount`
  - `monthly_discount_limit`
  - `monthly_remaining_discount`
  - `source_url`
  - `source_title`
  - `raw_summary`
  - `confidence`
- `ingest_card_search` now accepts `--detail`.

Verification:

- `manage.py test cards`: 27 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Detail text parsing extracts `brand_scope` from Korean oil brand names.
2. Generic all-station wording keeps `brand_scope=all`.
3. Minimum payment amounts such as `건당 3만원 이상` parse to `30000`.
4. Per-transaction caps such as `1회 최대 5천원` parse to `5000`.
5. Monthly limits such as `월 통합 할인한도 2만원` parse to `20000`.
6. Detail enrichment updates an existing `CardCatalog` row instead of creating a duplicate.
7. Updated catalog rows remain `verification_status=unverified`.

Remaining risk:

1. Live detail-page DOM wording may require additional parser rules after a dry-run against the approved Naver card search domain.
2. `monthly_remaining_discount` is user-specific and is expected to remain empty for public catalog ingestion unless the source text explicitly exposes a non-private remaining amount.

## Refactor Feature Spec v1.2 Live Card Detail Calibration Slice QA

Date: 2026-05-20

Scope:

- Run live `ingest_card_search --detail --dry-run` against the approved Naver card search domain
- Calibrate detail parsing against observed live detail-page wording
- Save enriched detail parsing results back to `CardCatalog` only after dry-run
- Keep all live-ingested catalog rows `verification_status=unverified`
- Keep recommendation calculation untouched and outside card ingestion

Approved source:

```text
https://card-search.naver.com/list?companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC
```

Live dry-run findings:

1. Some detail pages contain annual-fee cashback copy such as `100% 연회비 캐시백`; parser now prefers fuel-context discount values over global percentages.
2. Some detail pages put non-fuel percentages before fuel percentages on the same line; parser now prefers discount values near `주유`, `충전`, `LPG`, or related fuel keywords.
3. Previous-month spend requirements such as `직전 1개월 합계 30만원 이상` and `전월실적50만원이상` are not saved as `min_payment_amount` or `monthly_discount_limit`.
4. Console output sanitizes non-breaking spaces so Windows `cp949` stdout does not abort dry-run reporting.

Live ingestion result:

- Dry-run completed without saving.
- After parser calibration, live detail enrichment saved 9 unverified catalog candidates.
- Current catalog check found 11 total `CardCatalog` rows, all checked rows remained `verification_status=unverified`.
- The previously misparsed `삼성카드 taptap S` monthly limit was cleared back to empty.

Verification:

- `manage.py test cards`: 31 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Annual-fee cashback percentages do not override fuel benefit percentages.
2. Fuel-adjacent discount values win when multiple percentages appear in detail text.
3. Previous-month spend thresholds are not treated as per-transaction minimum payment amounts.
4. Previous-month spend thresholds are not treated as monthly discount limits.
5. Live detail enrichment updates `CardCatalog` rows while preserving `unverified` status.

Remaining risk:

1. Public detail pages often omit exact monthly fuel discount caps in easily machine-readable text, so uncertain limits intentionally remain empty for user confirmation.
2. `brand_scope` remains conservative and defaults to `all` unless a known fuel brand is explicitly detected in fuel-context text.

## Refactor Feature Spec v1.2 Naver Map Recommendation Display Slice QA

Date: 2026-05-20

Scope:

- Add presentation-only map metadata to the recommendation quote contract
- Add Naver Maps frontend script loading through `VITE_NAVER_MAPS_CLIENT_ID`
- Add degraded map state when the key is missing or the script fails
- Display recommendation and candidate station markers from backend response coordinates
- Synchronize marker selection with candidate list selection
- Keep recommendation ranking, distance, and cost calculations out of the frontend map layer

Contract changes:

- `docs/api_contracts/recommendations_quote.json` now documents `meta.map_display` as presentation-only metadata.
- Existing `recommendation.station.latitude`, `recommendation.station.longitude`, and `candidates[].station` coordinates remain the source for map display.
- Ranking and calculation contracts were not changed.

Verification:

- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed
- Browser smoke test with no Naver Maps key: blocked because the local Vite dev server could not start in the sandbox (`vite.config.js` access error). Backend dev server health check returned 200.

Covered cases:

1. Missing `VITE_NAVER_MAPS_CLIENT_ID` is handled as a degraded map state instead of a recommendation API failure.
2. Recommendation result and candidate list remain independent of map loading.
3. The frontend uses backend-provided candidate order and station coordinates only.
4. Marker/list selection updates UI selection state without recomputing rank, distance, or cost.
5. Card ingestion, `CardCatalog`, Selenium, and recommendation calculation code were not changed.

Remaining risk:

1. A live browser check should be repeated in an environment where the Vite dev server can start.
2. Real Naver Maps rendering should be verified with a valid client ID in a non-secret frontend environment variable.

## Refactor Feature Spec v1.2 Recommendation Context Flow Slice QA

Date: 2026-05-20

Scope:

- Add a recommendation-screen context panel for saved vehicle and active card state
- Add quick actions from the recommendation screen to vehicle and card management
- Return to the recommendation screen after saving a vehicle profile
- Keep context display as frontend workflow aid only

Contract changes:

- `docs/04_frontend_components.md` now documents `RecommendationContextPanel.vue`.
- No API contract changes were required.
- Recommendation ranking, distance, card discount, and cost contracts were not changed.

Verification:

- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. Authenticated users can see whether a saved vehicle is available for backend fallback.
2. Authenticated users can see the active saved card count before requesting a quote.
3. Recommendation screen actions can open vehicle and card management without changing quote calculation.
4. Saving a vehicle refreshes saved vehicle state and returns to the recommendation screen.
5. Frontend changes do not add recommendation ranking, distance, discount, or cost recalculation.
6. Card ingestion, `CardCatalog`, Selenium, and `backend/stations/services.py` were not changed.

Remaining risk:

1. Browser smoke should be repeated when the Vite dev server can start in the local environment.
2. Broader Korean copy cleanup remains a separate UX polish slice.

## Refactor Feature Spec v1.2 Frontend State Feedback Slice QA

Date: 2026-05-20

Scope:

- Add geolocation loading and recoverable failure messages to the location control
- Add profile update loading, success, and error feedback
- Add catalog search empty/success/error messages
- Add card image load fallback for catalog, selected catalog draft, and active card list
- Preserve existing recommendation display and calculation boundaries

Contract changes:

- `docs/04_frontend_components.md` now documents state-feedback responsibilities for `LocationControl.vue`, `ProfileView.vue`, and `CardsView.vue`.
- No backend API contract changes were required.
- Recommendation ranking, distance, card discount, and cost contracts were not changed.

Verification:

- `npm.cmd run build`: passed
- `manage.py test`: 61 tests passed
- Static scan for mojibake patterns in `frontend/src` and `docs/04_frontend_components.md`: no matches
- Static scan for ranking/distance/cost recomputation in changed frontend files: no matches

Covered cases:

1. Browser geolocation unavailable, denied, or timed out now leaves manual coordinates usable with a clear message.
2. Profile save exposes loading, success, and error states.
3. Card catalog search reports empty results and failed requests without hiding existing card management.
4. Card image failures fall back to the local card icon.
5. Frontend changes do not add recommendation ranking, distance, discount, or cost recalculation.
6. Card ingestion, `CardCatalog`, Selenium, and `backend/stations/services.py` were not changed.

Remaining risk:

1. Browser smoke should still be repeated when the Vite dev server can start in the local environment.

## Refactor Feature Spec v1.2 Documentation Alignment Slice QA

Date: 2026-05-20

Scope:

- Add root project README
- Update backend README for card catalog, station nearby, ingestion, and data-boundary notes
- Update frontend README for map display, map fallback, context panel, card catalog, and state feedback
- Update API contract chunk index for catalog, ingestion, and Opinet contracts

Contract changes:

- No API request/response contract changes were required.
- Documentation now points implementers to existing endpoint chunks and recommendation boundary rules.

Verification:

- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed

Covered cases:

1. README documentation states that recommendation calculation remains in `backend/stations/services.py`.
2. Frontend README documents that map API failure must not block recommendation results.
3. Backend README documents that Selenium/CardCatalog data remains outside request-time recommendation ranking until confirmed or verified.
4. API contract README includes `cards_catalog.json`, `cards_ingestion.json`, and `stations_opinet.json`.

Remaining risk:

1. Browser smoke remains blocked until the local Vite dev server can start in this environment.

## Refactor Feature Spec v1.2 Final Regression and Browser Smoke Recovery Slice QA

Date: 2026-05-20

Scope:

- Re-check frontend component and recommendation API contracts before implementation
- Reproduce the Vite dev server smoke issue
- Recover local browser smoke in an environment where Vite can start
- Verify map fallback with no `VITE_NAVER_MAPS_CLIENT_ID`
- Re-scan recommendation calculation boundaries
- Run final backend tests and frontend production build

Contract changes:

- No request contract changes were required.
- `POST /api/v1/recommendations/quote/` now returns the already documented `meta.map_display` presentation-only object.
- The baseline no-card cost selection was moved back into `backend/stations/services.py` via `quote_baseline_without_card` so recommendation cost selection stays inside the stations service boundary.

Vite dev server finding:

- Sandboxed `npm.cmd run dev` still fails while esbuild resolves `frontend/vite.config.js` with `Cannot read directory "../../..": Access is denied.`
- Running the same command outside the sandbox starts Vite successfully.
- Because port `5173` was already in use, Vite selected `http://127.0.0.1:5174/`.
- The blocked cause is the sandboxed Windows directory access during Vite config loading, not an app configuration failure.

Browser smoke result:

- Browser smoke completed against `http://127.0.0.1:5174/` with the Django dev server at `http://127.0.0.1:8000/`.
- Initial recommendation POST reached Django but was rejected by CSRF origin validation for the Vite dev origin.
- Added dev-only trusted CSRF origins for `localhost` and `127.0.0.1` on ports `5173` and `5174`.
- Recommendation screen then rendered the backend-selected station, cost breakdown, recommendation reason, and backend-ordered candidates.
- With no `VITE_NAVER_MAPS_CLIENT_ID`, the map degraded to `NAVER_MAPS_CLIENT_ID_MISSING` without blocking recommendation results.
- Card catalog screen rendered and catalog search returned candidates without breaking the empty/success state flow.
- Browser screenshot: `frontend/final-regression-smoke.png`

Static boundary scan:

- Frontend scan for `sort`, `rank`, `haversine`, `effective_total_cost`, and `distance_km` found only display reads in `RecommendationResult.vue`, `CostBreakdown.vue`, and `CandidateList.vue`.
- Backend scan found recommendation calculation terms in `backend/stations/services.py`, serializers, tests, and view metadata wiring; baseline cost selection now lives in `backend/stations/services.py`.
- Selenium, CardCatalog ingestion, and card parser code were not changed.

Verification:

- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed
- Browser smoke: passed after running Vite outside the sandbox

Remaining risk:

1. Real Naver Maps rendering still requires a valid non-secret `VITE_NAVER_MAPS_CLIENT_ID` in the frontend environment.
2. Sandboxed Vite dev server remains blocked by Windows access restrictions, but the same command works outside the sandbox.

## Refactor Feature Spec v1.2 Contract and Artifact Alignment Slice QA

Date: 2026-05-20

Scope:

- Re-check repository root and current worktree state
- Re-check frontend, recommendation, and API chunk contracts before changes
- Align card catalog API chunk references with actual contract files
- Align recommendation card `source_type` contract with catalog-confirmed Selenium cards
- Prevent generated local server logs and pid files from appearing as new source artifacts

Contract changes:

- Added `docs/api_contracts/cards_catalog.json` for:
  - `GET /api/v1/cards/catalog/`
  - `POST /api/v1/me/cards/from-catalog/`
- Updated `docs/api_contracts/recommendations_quote.json` so request card `source_type` allows `selenium`, matching user-confirmed catalog cards.
- No runtime API behavior changes were required.

Artifact hygiene changes:

- Added `*.log` and `*.pid` to `.gitignore` so local Django/Vite smoke-server artifacts are not treated as source files.

Verification:

- JSON parse check for `docs/api_contracts/cards_catalog.json`: passed
- JSON parse check for `docs/api_contracts/recommendations_quote.json`: passed
- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed
- Frontend static scan for ranking/distance/cost recomputation terms found display-only reads in result components.
- Selenium/CardCatalog ingestion implementation and recommendation calculation implementation were not changed.

Remaining risk:

1. Real Naver Maps rendering still requires a valid non-secret `VITE_NAVER_MAPS_CLIENT_ID` in the frontend environment.
2. `cards_ingestion.json` still contains catalog-related sections for historical context; day-to-day endpoint work should use the new `cards_catalog.json` chunk.

## Refactor Feature Spec v1.2 Naver Maps Live Key Smoke Slice QA

Date: 2026-05-20

Scope:

- Use a user-provided frontend Naver Maps JavaScript Client ID through `VITE_NAVER_MAPS_CLIENT_ID`
- Run Vite with the key in the process environment only; do not hard-code it
- Verify recommendation results remain independent of map rendering
- Distinguish successful script insertion from Naver map authorization failure
- Add explicit frontend fallback for Naver `auth_fail` map tiles

Contract changes:

- No API request/response contract changes were required.
- Recommendation ranking, distance, discount, and cost contracts were not changed.

Live smoke result:

- Vite was started at `http://127.0.0.1:5173/` with `VITE_NAVER_MAPS_CLIENT_ID` set in the process environment.
- Recommendation request succeeded and rendered the backend-selected station, cost breakdown, reason, and backend-ordered candidates.
- Naver Maps script tag was inserted with `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=...`.
- The Naver map canvas returned `auth_fail.png`, indicating the key or allowed-domain/API-product configuration is not authorized for this local origin yet.
- The frontend now detects the `auth_fail` tile and degrades to `NAVER_MAPS_AUTH_FAILED` instead of leaving a blank or misleading map.
- Browser smoke screenshot: `frontend/naver-map-auth-fallback-smoke.png`

Verification:

- `manage.py test`: 61 tests passed
- `npm.cmd run build`: passed
- Frontend static scan for ranking/distance/cost recomputation terms found display-only reads in result components.
- Selenium/CardCatalog ingestion and recommendation calculation logic were not changed.

Remaining risk:

1. Real Naver Maps tile and marker rendering still requires fixing the Naver Console settings for the provided Client ID, most likely allowed service URL and/or Maps JavaScript API authorization for `http://127.0.0.1:5173`.
2. After the Naver Console configuration is corrected, repeat the same live smoke and expect marker rendering instead of `NAVER_MAPS_AUTH_FAILED`.

## Refactor Feature Spec v1.2 Opinet Live Key Health Slice QA

Date: 2026-05-20

Scope:

- Use a user-provided `OPINET_API_KEY` through the backend process environment only
- Re-check the Opinet synchronization contract before implementation
- Add a non-writing Opinet live health-check path
- Verify the recommendation API remains decoupled from Opinet network calls

Official Opinet references checked:

- Opinet API overview page documents that oil price APIs require a KNOC-issued key and include free APIs such as national averages and station detail APIs.
- `detailById.do` documents station detail lookup by Opinet station ID.
- `avgAllPrice.do` documents current national average fuel prices and is suitable for non-writing API health checks.

Contract changes:

- Updated `docs/api_contracts/stations_opinet.json` with:
  - `--dry-run`: environment/key configuration validation without writes
  - `--health-check`: call `avgAllPrice.do` and report returned row count without writes
- No recommendation request/response contract changes were required.

Implementation changes:

- Added `OpinetClient.fetch_average_price_rows()` for the official `avgAllPrice.do` endpoint.
- Added `sync_opinet_prices --health-check`.
- The health-check path does not create or update `GasStation` or `FuelPrice` rows.
- Station-level Opinet price mapping remains outside this slice because local dummy stations use `DUMMY-*` external IDs, not Opinet `UNI_ID` values.

Live smoke result:

- `sync_opinet_prices --dry-run` with `OPINET_API_KEY` set in the backend process environment: passed with `0 rows available`.
- Direct official `detailById.do` smoke with sample station ID returned HTTP 200 and an empty `OIL` array.
- `sync_opinet_prices --health-check` called `avgAllPrice.do`, returned HTTP 200 through the command path, and reported `0 rows returned`.
- The key value was not written to code, docs, or frontend artifacts.

Verification:

- `manage.py test`: 64 tests passed
- `npm.cmd run build`: passed
- JSON parse check for `docs/api_contracts/stations_opinet.json`: passed
- Static scan found `OPINET_API_KEY` references only as environment variable names or test placeholder values.
- Frontend static scan for ranking/distance/cost recomputation terms found display-only reads in result components.

Remaining risk:

1. The provided Opinet key currently reaches the official endpoint but returns empty result arrays, so it may need API authorization/activation or endpoint-specific permission confirmation in Opinet.
2. Full station-level synchronization still needs a separate mapping slice for Opinet station IDs, product code mapping, coordinate conversion if needed, and `FuelPrice(source=opinet)` writes.

## Refactor Feature Spec v1.2 Opinet Station Sync Mapping Contract Slice QA

Date: 2026-05-20

Scope:

- Re-check repository root and current worktree state before changes
- Re-check Opinet synchronization, recommendation algorithm, and QA documents before implementation
- Confirm station-level Opinet endpoint candidates from official Opinet documentation only
- Document station identity, brand, product-code, and coordinate mapping before any DB write implementation
- Add non-writing parse/mapping helpers with tests
- Keep recommendation quote requests decoupled from Opinet network calls

Official Opinet references checked:

- `detailById.do` is the official station detail-by-ID endpoint and returns `UNI_ID`, station metadata, KATEC coordinate fields, and `OIL_PRICE` rows.
- `aroundAll.do` is the official radius search endpoint and requires KATEC `x`/`y`, radius, product code, and sort option.
- Both official pages document `GIS_X_COOR` and `GIS_Y_COOR` as KATEC, so SmartFuel must not write them to WGS84 latitude/longitude fields until conversion is implemented and verified.

Contract changes:

- Updated `docs/api_contracts/stations_opinet.json` with station-level mapping design:
  - `UNI_ID` -> `GasStation.external_station_id`
  - `POLL_DIV_CD`/documented sample `POLL_DIV_CO` -> `GasStation.brand`
  - `B027` -> `gasoline`
  - `D047` -> `diesel`
  - `B034` -> `premium_gasoline`
  - `K015` -> `lpg`
  - `C004` remains unsupported for vehicle recommendation
  - KATEC coordinates are held as source fields only until KATEC-to-WGS84 conversion is verified
- Updated `docs/03_recommendation_algorithm.md` with the stored-price boundary and Opinet request-time prohibition.

Implementation changes:

- Added pure Opinet mapping helpers in `backend/stations/opinet_client.py`.
- Added mapping tests for station ID, brand mapping, product-code mapping, unsupported products, and coordinate non-conversion.
- Tightened `sync_opinet_prices --health-check` so it does not call station-level fetch paths.
- No `GasStation` or `FuelPrice(source=opinet)` writes were added.
- Frontend, Selenium/CardCatalog, and recommendation calculation code were not changed.

Verification:

- `docs/api_contracts/stations_opinet.json` JSON parse: passed
- `manage.py test`: 68 tests passed
- `npm.cmd run build`: passed
- Static scan found Opinet network/client usage only in backend Opinet synchronization code and tests.
- Frontend static scan for ranking/distance/cost recomputation terms found display-only reads in result components.

Remaining risk:

1. Station-level writes still require a verified KATEC-to-WGS84 conversion implementation.
2. Real Opinet station matching needs live `UNI_ID` discovery and confirmation after API key endpoint authorization returns non-empty station data.
