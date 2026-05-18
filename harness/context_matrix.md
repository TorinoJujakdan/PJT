# SmartFuel Context Matrix

This file defines which documents each agent role may load.

The goal is scope-based injection: do not load the full project context when a role only needs a small slice.

## 1. Agent Context Scopes

### Architect

Allowed context:

- `docs/01_architecture_spec.md`
- `docs/02_api_blueprint.json`
- `docs/03_recommendation_algorithm.md`
- `docs/04_frontend_components.md`
- `docs/05_test_reports.md`
- `harness/rules.md`
- `harness/workflows.md`

Use this role only for contract design, cross-domain changes, or workflow changes.

### Backend Coder

Allowed context:

- `docs/01_architecture_spec.md`
- `docs/03_recommendation_algorithm.md`
- one relevant file from `docs/api_contracts/`
- `docs/09_card_benefit_data_strategy.md` only for Slice 4 card work

Do not load the full `docs/02_api_blueprint.json` unless the needed endpoint chunk does not exist.

If a chunk is missing, extract only the active endpoint from `docs/02_api_blueprint.json`, create a chunk file, and continue from the chunk.

### Frontend Coder

Allowed context:

- `docs/04_frontend_components.md`
- one relevant file from `docs/api_contracts/`
- `docs/09_card_benefit_data_strategy.md` only for card image or card discovery UI work

Do not load backend architecture documents unless the UI task explicitly needs backend domain reasoning.

### QA Agent

Allowed context:

- `docs/05_test_reports.md`
- `docs/03_recommendation_algorithm.md`, only the Error Cases and relevant formula sections
- one relevant file from `docs/api_contracts/`

Do not load frontend component plans unless testing UI behavior.

### DevOps Agent

Allowed context:

- `docs/01_architecture_spec.md`, only deployment and environment sections
- `ops/`
- `harness/workflows.md`, only Deployment Workflow

Do not load recommendation math unless deployment smoke tests require a sample request.

## 2. API Chunking Rule

`docs/02_api_blueprint.json` is the canonical full contract, but workers should not inject it wholesale.

Workers must prefer endpoint-specific chunks:

```text
docs/api_contracts/
```

Naming convention:

```text
{domain}_{endpoint_name}.json
```

Examples:

- `recommendations_quote.json`
- `stations_nearby.json`

## 3. Lazy Loading Rule

Task prompts should point to files instead of pasting document contents.

Good:

```text
Your task instruction is in docs/04_frontend_components.md.
Read that file and docs/api_contracts/recommendations_quote.json, then implement RecommendView.vue.
```

Avoid:

```text
Here is the whole architecture, API contract, algorithm, frontend plan, and QA log...
```

## 4. Progressive Unveiling Rule

Do not implement all recommendation slices at once.

Recommended task shape:

```text
Today implement slice 1 and slice 2 only:
1. Station candidate search
2. Fuel-price-only recommendation
```

Only load card discount context when implementing slice 4 or later.
