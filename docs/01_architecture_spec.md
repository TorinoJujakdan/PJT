# SmartFuel Architecture Specification

## 1. Service Goal

SmartFuel recommends the most reasonable gas station from the user's current location.

The service compares:

- fuel price
- user's vehicle fuel efficiency
- user's credit card fuel discount
- travel cost to reach the station

The primary product promise is:

```text
Recommend the station with the lowest practical total cost, not just the lowest posted fuel price.
```

## 2. Workspace Root

This project is built from scratch in:

```text
C:\Users\SSAFY\Desktop\pjtworkspace
```

No previous SmartFuel project outside this workspace is part of the source of truth.

## 3. Project Layout

```text
pjtworkspace/
├── docs/
│   ├── 01_architecture_spec.md
│   ├── 02_api_blueprint.json
│   ├── 03_recommendation_algorithm.md
│   ├── 04_frontend_components.md
│   ├── 05_test_reports.md
│   ├── 06_erd.md
│   ├── 07_use_case_diagram.md
│   ├── 08_gantt_chart.md
│   └── 09_card_benefit_data_strategy.md
├── backend/
│   ├── core/
│   ├── accounts/
│   ├── stations/
│   ├── vehicles/
│   └── cards/
├── frontend/
│   └── src/
│       ├── components/
│       ├── views/
│       ├── stores/
│       └── api/
├── ops/
└── harness/
```

## 4. Backend Domains

### 4.1 `core`

Owns Django project configuration.

Responsibilities:

- settings
- URL routing root
- environment loading
- CORS
- DRF configuration
- health check wiring

### 4.2 `accounts`

Owns authentication and user identity.

Responsibilities:

- registration
- login
- token/session policy
- current user profile API

### 4.3 `vehicles`

Owns vehicle information used for recommendation.

Primary model:

```text
VehicleProfile
```

Required fields:

- user
- fuel_type
- fuel_efficiency_kmpl

### 4.4 `cards`

Owns card discount policies and user's selected cards.

Primary models:

```text
CardPolicy
UserCard
```

Required policy fields:

- card name
- issuer name
- discount type
- discount value
- target brand scope
- minimum payment amount
- maximum discount amount
- monthly remaining discount
- source type
- verification status
- card image URL
- source URL

Card policies can come from:

- user manual input
- Naver-based discovery
- admin-seeded data
- issuer-provided data

Naver-discovered card policies must be confirmed by the user or verified by an admin before they affect recommendations.

### 4.5 `stations`

Owns gas station data, fuel price data, station search, and recommendation service orchestration.

Primary models:

```text
GasStation
FuelPrice
```

Recommended service file:

```text
backend/stations/services.py
```

The recommendation algorithm is defined in:

```text
docs/03_recommendation_algorithm.md
```

## 5. API Contract

The backend and frontend must follow:

```text
docs/02_api_blueprint.json
```

The canonical recommendation endpoint is:

```http
POST /api/v1/recommendations/quote/
```

The frontend must not recompute recommendation ranking.

## 6. Data Source Strategy

MVP data source:

- local dummy station data

Target data source:

- Opinet fuel price data
- Naver Developers Search API for card benefit discovery
- optional navigation API route distance

Fallback rule:

```text
External API failure must not block local development or QA.
```

## 7. Development Phases

### Phase 1: Design

- freeze architecture spec
- freeze recommendation algorithm
- freeze API contract
- define frontend component map
- define QA scenarios

### Phase 2: Implementation

- scaffold Django backend
- implement station candidate search
- implement recommendation service
- implement account, vehicle, and card APIs
- implement Vue frontend

### Phase 3: Inspection

- backend unit/API tests
- frontend build verification
- recommendation scenario QA
- Docker smoke test

### Phase 4: Deployment

- Docker Compose
- environment variable templates
- health check
- deployment checklist

## 8. Design Diagrams

Use these documents to read the whole project flow visually:

- `docs/06_erd.md`: target data model and domain relationships
- `docs/07_use_case_diagram.md`: user, admin, and external API interactions
- `docs/08_gantt_chart.md`: phase-based project schedule and milestones
- `docs/09_card_benefit_data_strategy.md`: manual and Naver-based card benefit data strategy
