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

Status: pending implementation

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
