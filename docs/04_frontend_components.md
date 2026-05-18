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

### `ProfileView.vue`

Responsibilities:

- show account state
- login/logout entry
- link to vehicle and card settings

## 3. Components

### `LocationControl.vue`

Inputs:

- browser current location
- manual latitude/longitude

Emits:

- normalized location object

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
