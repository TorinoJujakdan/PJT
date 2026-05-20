# SmartFuel QA Report Log (Active Summary)

This file maintains the active summary of quality gate verifications, regression status, and official environment configurations. 

> [!NOTE]
> Detailed QA records for past development slices (Slice 1 ~ Slice 7, Refactor Spec v1.1, v1.2 detailed calibration slices) have been archived to [05_test_reports_archive.md](file:///c:/Users/SSAFY/Desktop/pjtworkspace/docs/archive/05_test_reports_archive.md) to maximize token efficiency and maintain a clean workspace.

---

## 1. Active Quality Gate Status

* **Backend Unit/API Tests**: **Passed (68/68 tests passed)**
* **Frontend Production Build**: **Passed (`npm run build` completed successfully)**
* **Harness Recommendation Scenarios**: **100% Verified**
* **Docker Smoke Test Status**: **Ready for Phase 4 deployment**

---

## 2. Latest Verification Records

### 2.1 Refactor Feature Spec v1.2 Live Card Detail Calibration
* **Date**: 2026-05-20
* **Scope**: Selenium-based card catalog ingestion dry-run calibration against `card-search.naver.com`.
* **Ingestion Results**: 11 total `CardCatalog` rows saved as `unverified`.
* **Calibration Rule**: Prevented annual-fee cashback percentages from overriding fuel benefit percentages. Decoupled public catalog data from request-time recommendation calculations.

### 2.2 Refactor Feature Spec v1.2 Naver Maps Live Key Smoke
* **Date**: 2026-05-20
* **Scope**: Geolocation and Naver Maps display integration.
* **Findings**: In the absence of a secret map key, the map gracefully degrades to `NAVER_MAPS_AUTH_FAILED` without blocking recommendation output. 
* **Hygiene**: Dev-only trusted CSRF origins configured for local Vite ports (`5173`, `5174`).

### 2.3 Refactor Feature Spec v1.2 Opinet Station Sync Mapping
* **Date**: 2026-05-20
* **Scope**: Non-writing parse/mapping helpers for Opinet integration (`avgAllPrice.do` and `detailById.do`).
* **Verification**: `sync_opinet_prices --health-check` runs without database writes. Geolocation and station matching remain decoupled from external Opinet requests.

---

## 3. Verified Harness QA Scenarios

1. **Cheapest/lowest effective-cost station** is recommended when no card exists. (Verified)
2. **A more expensive station** is recommended when a confirmed card discount makes it cheaper. (Verified)
3. **A discounted distant station** is rejected when travel cost exceeds the discount benefit. (Verified)
4. **No candidate station** returns `NO_STATION_CANDIDATE` (HTTP 404). (Verified)
5. **Missing vehicle efficiency** returns `MISSING_VEHICLE_EFFICIENCY` (HTTP 400). (Verified)
6. **Invalid location coordinates** returns `INVALID_LOCATION` (HTTP 400). (Verified)
7. **Unsupported fuel type** returns `UNSUPPORTED_FUEL_TYPE` (HTTP 400). (Verified)

---

## 4. Current Hygiene Configuration
* Local servers, logs (`*.log`), and process files (`*.pid`) are safely added to `.gitignore`.
* Empty placeholder files (`.gitkeep`) are cleaned up from active packages.
* Inactive or outdated project specifications are archived in `docs/archive/`.
