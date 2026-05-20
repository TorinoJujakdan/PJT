# SmartFuel

SmartFuel recommends the gas station with the lowest practical refueling cost by combining station prices, travel cost, vehicle efficiency, and confirmed card benefits.

## Current Scope

- Django REST Framework backend with account, vehicle, card, station, and recommendation APIs.
- Vue 3 + Vite frontend for recommendation, account, vehicle, card catalog, and map display flows.
- Recommendation calculation stays in `backend/stations/services.py`.
- Frontend displays backend recommendation results and must not recompute ranking, distance, discount, or cost.
- Selenium card ingestion is a controlled offline/management-command flow and does not run inside recommendation requests.

## Key Contracts

- Recommendation algorithm: `docs/03_recommendation_algorithm.md`
- API chunks: `docs/api_contracts/`
- Frontend component contract: `docs/04_frontend_components.md`
- QA log: `docs/05_test_reports.md`

## Verification

```powershell
cd backend
& 'C:\Users\SSAFY\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manage.py test

cd ..\frontend
npm.cmd run build
```
