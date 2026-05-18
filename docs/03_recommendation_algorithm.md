# SmartFuel Recommendation Algorithm Specification

## 1. Purpose

SmartFuel recommends the gas station with the lowest practical cost from the user's current location.

The recommendation must not simply choose the cheapest fuel price. It must compare the final expected cost after applying:

- fuel price
- user's credit card discount
- vehicle fuel efficiency
- travel cost to reach the station

The core decision rule is:

```text
effective_total_cost =
  refuel_cost
  - card_discount_amount
  + travel_cost
```

The station with the lowest `effective_total_cost` is recommended.

## 2. Required Inputs

### 2.1 User Location

```json
{
  "latitude": 37.501,
  "longitude": 127.039
}
```

Rules:

- `latitude` must be between `-90` and `90`.
- `longitude` must be between `-180` and `180`.
- Both values are required for recommendation.

### 2.2 Fuel Type

Supported fuel types:

```text
gasoline
diesel
lpg
premium_gasoline
```

The first implementation may support only `gasoline` and `diesel`, but the API contract must keep the enum above.

### 2.3 Target Refuel Amount

`target_liters` is the expected amount of fuel the user plans to buy.

Rules:

- Unit: liter
- Required for stateless recommendation requests.
- Default may be `50.0` only when a product decision explicitly allows default recommendation.
- Valid range: `1.0` to `150.0`

SmartFuel v1 uses `target_liters` instead of a target KRW amount because it compares the same fuel quantity across stations and therefore reflects fuel-price differences directly.

### 2.4 Vehicle Fuel Efficiency

`fuel_efficiency_kmpl` means kilometers per liter.

Rules:

- If the user has a saved vehicle profile and the request omits this value, the saved value is used.
- If the user is anonymous and omits this value, the API returns `MISSING_VEHICLE_EFFICIENCY`.
- Valid range: `1.0` to `50.0`

### 2.5 User Cards

The recommendation engine receives zero or more card discount policies.

No card is a valid case. In that case:

```text
card_discount_amount = 0
```

Card policies may come from manual user input, admin-seeded data, issuer data, or Naver-based discovery.

Only the following card policies can affect recommendation ranking:

```text
verification_status = user_confirmed
verification_status = admin_verified
source_type = manual
```

Unverified Naver-discovered policies must be shown as suggestions only and must not affect final ranking.

## 3. Station Candidate Search

### 3.1 Bounding Box First Filter

The server must not calculate Haversine distance against every station row.

First, calculate a latitude/longitude bounding box around the user location.

Default:

```text
radius_km = 15
```

Maximum:

```text
radius_km = 30
```

The database query filters stations inside the bounding box first.

### 3.2 Haversine Second Filter

After the bounding box query, calculate exact straight-line distance with Haversine.

Only stations where:

```text
distance_km <= radius_km
```

remain as candidates.

### 3.3 Future Route API Upgrade

For the first implementation, Haversine distance is accepted.

When a navigation API is available, `distance_km` may be replaced by route distance. The response must indicate which distance source was used:

```text
haversine
navigation_api
```

## 4. Cost Calculation

### 4.1 Refuel Cost

```text
refuel_cost = fuel_price_per_liter * target_liters
```

Example:

```text
fuel_price_per_liter = 1650
target_liters = 50
refuel_cost = 82,500 KRW
```

### 4.2 Travel Cost

Default travel mode:

```text
round_trip
```

Formula:

```text
travel_distance_km = distance_km * 2
travel_fuel_liters = travel_distance_km / fuel_efficiency_kmpl
travel_cost = travel_fuel_liters * fuel_price_per_liter
```

The first implementation uses the candidate station's selected fuel price as the travel fuel price.

Example:

```text
distance_km = 5
fuel_efficiency_kmpl = 10
fuel_price_per_liter = 1650

travel_distance_km = 10
travel_fuel_liters = 1
travel_cost = 1,650 KRW
```

### 4.3 Card Discount

A card discount policy may support one of the following discount types:

```text
per_liter
percentage
fixed_amount
```

#### Per-liter Discount

```text
raw_discount = discount_value * target_liters
```

Example:

```text
discount_value = 80 KRW per liter
target_liters = 50
raw_discount = 4,000 KRW
```

#### Percentage Discount

```text
raw_discount = refuel_cost * discount_value / 100
```

Example:

```text
discount_value = 5
refuel_cost = 82,500
raw_discount = 4,125 KRW
```

#### Fixed Amount Discount

```text
raw_discount = discount_value
```

### 4.4 Discount Constraints

Discount policies may have constraints.

Supported constraints:

```text
brand_scope
min_payment_amount
max_discount_amount
monthly_remaining_discount
```

The final discount is:

```text
card_discount_amount =
  min(
    raw_discount,
    max_discount_amount if present,
    monthly_remaining_discount if present
  )
```

If the station brand does not match `brand_scope`, the discount is `0`.

If `refuel_cost < min_payment_amount`, the discount is `0`.

When multiple user cards are available, calculate the discount for each card and use the best card for that station.

```text
best_card_discount = max(discount_amount_by_card)
```

The response must include the selected card for each candidate if a card discount is applied.

The selected card payload must include:

- card name
- issuer name
- card image URL, if available
- source type
- verification status
- discount type
- discount value
- calculated discount amount

### 4.5 Effective Total Cost

```text
effective_total_cost =
  refuel_cost
  - best_card_discount
  + travel_cost
```

The recommended station is the candidate with the lowest `effective_total_cost`.

## 5. Baseline and Saving Calculation

The baseline is the best candidate when card discounts are ignored.

```text
baseline_cost =
  min(refuel_cost + travel_cost among candidates)
```

The saving of a recommended station is:

```text
estimated_saving = baseline_cost - effective_total_cost
```

Rules:

- If there is no card benefit, `estimated_saving` may be `0`.
- If all candidate cards produce no discount, the recommendation still works as a fuel-price and travel-cost optimizer.

## 6. Ranking Rules

Candidates are sorted by:

1. `effective_total_cost` ascending
2. `distance_km` ascending
3. `fuel_price_per_liter` ascending
4. `station_id` ascending

The first candidate after sorting is the recommendation.

## 7. Rounding Rules

For internal ranking:

- Use decimal calculation.

For API response:

- KRW amounts are rounded to the nearest integer.
- `distance_km` is rounded to 2 decimal places.
- `target_liters` is rounded to 2 decimal places.
- `fuel_efficiency_kmpl` is rounded to 2 decimal places.

## 8. Error Cases

### 8.1 No Candidate Station

When no station exists inside the search radius:

```http
404 Not Found
```

Response code:

```text
NO_STATION_CANDIDATE
```

### 8.2 Invalid Location

```http
400 Bad Request
```

Response code:

```text
INVALID_LOCATION
```

### 8.3 Missing Vehicle Efficiency

```http
400 Bad Request
```

Response code:

```text
MISSING_VEHICLE_EFFICIENCY
```

### 8.4 Unsupported Fuel Type

```http
400 Bad Request
```

Response code:

```text
UNSUPPORTED_FUEL_TYPE
```

## 9. Recommendation Explanation Contract

Every successful recommendation response must explain why the station was selected.

The explanation must include:

- base fuel price
- selected card discount, if any
- selected card name and issuer, if any
- card image URL, if available
- travel cost
- final effective total cost
- estimated saving against baseline
- comparison reason against cheaper or closer alternatives

The response must make it possible for the frontend to display:

```text
"카드 할인과 이동 비용을 반영했을 때 이 주유소가 가장 합리적입니다."
```

without recalculating the result on the client.

## 10. Implementation Ownership

Recommended backend location:

```text
backend/stations/services.py
```

Required service functions:

```text
get_station_candidates(location, radius_km, fuel_type)
calculate_card_discount(station, refuel_cost, target_liters, user_cards)
calculate_travel_cost(distance_km, fuel_efficiency_kmpl, fuel_price_per_liter)
rank_recommendations(candidates, user_context)
```

The API view must call the service layer. Recommendation math must not be embedded directly in the view.
