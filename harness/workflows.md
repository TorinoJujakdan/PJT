# SmartFuel Harness Workflows

## 1. Design Workflow

```text
problem statement
-> recommendation algorithm contract
-> API contract
-> backend implementation plan
-> frontend implementation plan
-> QA scenarios
```

## 2. Implementation Workflow

```text
identify role and feature slice
-> load scoped context from harness/context_matrix.md
-> load relevant API chunk from docs/api_contracts/
-> contract check
-> model/service implementation
-> serializer/view implementation
-> frontend API client update
-> frontend screen update
-> local verification
```

## 3. Recommendation Feature Slice

Recommended implementation order:

1. Station candidate search with bounding box and Haversine distance
2. Fuel-price-only recommendation
3. Vehicle fuel-efficiency travel cost
4. Card discount calculation
5. Final effective total cost ranking
6. Explanation fields in API response
7. Frontend recommendation result display

### Slice Context Rules

Slice 1:

- Load `docs/01_architecture_spec.md`
- Load `docs/api_contracts/stations_nearby.json`
- Read only candidate search sections from `docs/03_recommendation_algorithm.md`
- Do not load card policy context

Slice 2:

- Load `docs/01_architecture_spec.md`
- Load `docs/api_contracts/recommendations_quote.json`
- Read fuel price, candidate search, and ranking sections from `docs/03_recommendation_algorithm.md`
- Do not load card policy context

Slice 3:

- Add vehicle fuel-efficiency and travel-cost sections from `docs/03_recommendation_algorithm.md`

Slice 4:

- Add card discount sections from `docs/03_recommendation_algorithm.md`
- Add card API chunk when it exists
- Add `docs/09_card_benefit_data_strategy.md`
- Keep Naver discovery separate from recommendation math
- Do not use unverified discovered card policies in ranking

Slice 5:

- Read full ranking and rounding sections from `docs/03_recommendation_algorithm.md`

Slice 6:

- Read recommendation explanation contract from `docs/03_recommendation_algorithm.md`
- Verify `docs/api_contracts/recommendations_quote.json` response fields

Slice 7:

- Load `docs/04_frontend_components.md`
- Load `docs/api_contracts/recommendations_quote.json`
- Do not load backend implementation files unless debugging an API mismatch

## 4. QA Workflow

Required QA scenarios:

1. Cheapest station is recommended when no card exists.
2. A more expensive station is recommended when card discount makes it cheaper.
3. A distant discounted station is rejected when travel cost removes the benefit.
4. No candidate station returns `NO_STATION_CANDIDATE`.
5. Missing vehicle efficiency returns `MISSING_VEHICLE_EFFICIENCY`.
6. Invalid location returns `INVALID_LOCATION`.
7. Unsupported fuel type returns `UNSUPPORTED_FUEL_TYPE`.

## 5. Deployment Workflow

```text
environment check
-> backend test
-> frontend build
-> docker compose build
-> health check
-> recommendation smoke test
```
