# SmartFuel Harness Rules

## 1. Contract First

- `docs/02_api_blueprint.json` is the API contract.
- `docs/03_recommendation_algorithm.md` is the recommendation contract.
- Backend and frontend implementation must follow these files.
- If implementation requires a contract change, update the document first.
- Worker agents should use endpoint chunks in `docs/api_contracts/` instead of loading the full API blueprint.
- Role-specific context limits are defined in `harness/context_matrix.md`.

## 2. Recommendation Boundary

- Recommendation math belongs in `backend/stations/services.py`.
- API views may validate input and format responses, but must not own ranking logic.
- The frontend must display recommendation output from the API and must not recompute ranking.

## 3. Data Source Resilience

- External oil price API failure must not block local development.
- Dummy station data or cached station data must support recommendation development.
- The response should expose whether distance was calculated with `haversine` or `navigation_api`.

## 4. Quality Gates

Before a feature is considered complete:

- API request and response match the relevant endpoint chunk in `docs/api_contracts/`.
- The relevant endpoint chunk remains consistent with `docs/02_api_blueprint.json`.
- Recommendation result matches `docs/03_recommendation_algorithm.md`.
- Error cases are covered.
- QA findings are recorded in `docs/05_test_reports.md` when that file exists.

## 5. Multi-Agent Ownership

- Architect owns contracts and workflow.
- Backend Coder owns Django models, serializers, views, services, and tests.
- Frontend Coder owns Vue views, state, API client modules, and UI states.
- QA Agent owns behavior checks and regression scenarios.
- DevOps Agent owns Docker, environment variables, and deployment checks.

## 6. Scope-Based Injection

- Do not inject every document into every task.
- Follow `harness/context_matrix.md` for role-specific document loading.
- Prefer file references over pasted document contents.
- Load large files lazily and only when a smaller chunk is unavailable.

## 7. Progressive Implementation

- Implement recommendation features by slice.
- Do not load or implement card-discount context before slice 4.
- Do not implement frontend recommendation display before the backend response contract is stable.
- A task prompt should name the exact slice being implemented.
