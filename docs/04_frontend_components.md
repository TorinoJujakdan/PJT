# SmartFuel Frontend Component Plan

## 1. Frontend Goal

The frontend should help the user answer one question quickly:

```text
Where should I refuel right now to spend the least practical amount?
```

The UI displays the backend recommendation result and explains the cost breakdown. It must not recalculate recommendation ranking.

## 2. Views

### `RecommendView.vue`

Main screen.

Responsibilities:

- get current location or accept manual location
- choose fuel type
- enter target liters
- show saved vehicle and active card context for authenticated users
- provide entry points to vehicle and card settings without changing recommendation math
- call recommendation API
- show recommended station
- show cost breakdown and candidate comparison

### `VehicleView.vue`

Responsibilities:

- create or update vehicle fuel efficiency
- select default fuel type

### `CardsView.vue`

Responsibilities:

- list user's registered cards
- add card policy
- remove card policy
- show loading, empty, success, and error states for catalog search and card save/delete actions

### `ProfileView.vue`

Responsibilities:

- show account state
- login/logout entry
- link to vehicle and card settings
- show loading, success, and error feedback for profile updates

## 3. Components

### `LocationControl.vue`

Inputs:

- Naver Geocoding-backed address or place search
- browser current location with reverse geocoded address label
- map click coordinate updates from the recommendation map

Emits:

- normalized location object

States:

- loading while geocoding or browser geolocation is pending
- empty search results
- selected departure address, coordinate, and browser accuracy when available
- field-level message when geolocation, geocoding, or reverse geocoding fails

### `FuelTargetControl.vue`

Inputs:

- fuel type
- target liters

Rules:

- target liters range: `1.0` to `150.0`

### `RecommendationResult.vue`

Displays:

- recommended station name
- brand
- distance
- final effective total cost
- estimated saving
- selected card, if any
- selected card image, if available
- recommendation reason

### `CostBreakdown.vue`

Displays:

- refuel cost
- card discount amount
- travel cost
- effective total cost

### `CandidateList.vue`

Displays alternative candidates returned by the API.

Sorting is already decided by the backend.

### `RecommendationContextPanel.vue`

Displays:

- whether the recommendation request can use a saved vehicle profile
- active saved card count
- quick actions to open vehicle and card management

Rules:

- The panel is a workflow aid only.
- It must not calculate recommendation ranking, distance, discounts, or costs.
- The recommendation request still decides whether to include request vehicle fields or rely on backend saved-profile fallback.

### `VehicleProfileForm.vue`

Inputs:

- fuel type
- fuel efficiency km/L

### `CardPolicyForm.vue`

Inputs:

- card name
- issuer name
- discount type
- discount value
- brand scope
- discount constraints
- card image URL
- source URL
- user memo

### `CardDiscoverySearch.vue`

Searches card benefit candidates from Naver-based discovery results.

Displays:

- candidate card name
- issuer
- card image
- source title
- source URL
- verification status

The user must confirm or edit a discovered policy before it becomes active.

## 4. Stores

### `authStore`

Owns:

- current user
- token
- login/logout state

### `recommendationStore`

Owns:

- current request
- latest recommendation response
- loading state
- API error state

### `profileStore`

Owns:

- vehicle profile
- card policies

## 5. API Modules

```text
src/api/client.js
src/api/recommendations.js
src/api/stations.js
src/api/auth.js
src/api/vehicles.js
src/api/cards.js
```

Rules:

- All HTTP calls go through `src/api/client.js`.
- Auth token handling belongs in the API client.
- Views must call API modules, not raw Axios directly.
- Recommendation math remains on the backend.
