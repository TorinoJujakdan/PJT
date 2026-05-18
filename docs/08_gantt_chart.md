# SmartFuel Gantt Chart

This Gantt chart maps the current SmartFuel plan into the four project phases:

1. Design
2. Implementation
3. Inspection
4. Deployment

The schedule uses relative project days. Adjust the dates when the actual sprint start date changes.

```mermaid
gantt
    title SmartFuel Project Roadmap
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d

    section Phase 1 - Design
    Architecture spec freeze           :done, des1, 2026-05-18, 1d
    Recommendation algorithm freeze    :done, des2, 2026-05-18, 1d
    API contract freeze                :done, des3, 2026-05-18, 1d
    ERD and use case documentation     :done, des4, 2026-05-18, 1d
    Harness context and workflow rules :done, des5, 2026-05-18, 1d

    section Phase 2 - Backend Implementation
    Django project scaffold            :impl1, 2026-05-19, 1d
    Slice 1 station candidate search   :impl2, after impl1, 1d
    Slice 2 fuel-price-only recommend  :impl3, after impl2, 1d
    Slice 3 vehicle travel cost        :impl4, after impl3, 1d
    Slice 4 card policy and discovery  :impl5, after impl4, 1d
    Slice 4 card discount calculation  :impl5b, after impl5, 1d
    Slice 5 final ranking and reason   :impl6, after impl5, 1d
    Account vehicle card APIs          :impl7, after impl6, 2d

    section Phase 2 - Frontend Implementation
    Vue project scaffold               :front1, 2026-05-21, 1d
    API client and stores              :front2, after front1, 1d
    Recommendation view                :front3, after front2, 2d
    Vehicle and card settings views    :front4, after front3, 2d
    Error and loading states           :front5, after front4, 1d

    section Phase 3 - Inspection
    Backend unit and API tests         :qa1, 2026-05-27, 2d
    Recommendation scenario QA         :qa2, after qa1, 1d
    Frontend build and smoke test      :qa3, after qa2, 1d
    Integration test                   :qa4, after qa3, 1d
    QA report update                   :qa5, after qa4, 1d

    section Phase 4 - Deployment
    Dockerfiles and compose            :dep1, 2026-06-02, 1d
    Environment templates              :dep2, after dep1, 1d
    Health check and smoke test        :dep3, after dep2, 1d
    Deployment checklist               :dep4, after dep3, 1d
```

## Milestones

| Milestone | Exit Criteria |
|---|---|
| Design Complete | Architecture, API, algorithm, ERD, use case, and harness rules are documented |
| Backend MVP | Recommendation API returns ranked station candidates from dummy data |
| Personalized Recommendation | Vehicle efficiency and card discounts affect final ranking |
| Frontend MVP | User can request and view recommendation with cost breakdown |
| Inspection Complete | API tests, scenario QA, frontend build, and integration smoke test pass |
| Deployment Ready | Docker Compose, `.env.example`, health check, and deployment checklist are ready |

## Progressive Implementation Guardrail

Do not implement all recommendation logic at once.

Follow the slice order from `harness/workflows.md`:

```text
candidate search
-> fuel-price-only recommendation
-> vehicle travel cost
-> card discount
-> final ranking
-> explanation response
-> frontend display
```
