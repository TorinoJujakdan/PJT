# SmartFuel Frontend

Vue 3 + Vite frontend for SmartFuel.

The frontend consumes the API contract in `docs/02_api_blueprint.json`.

Frontend rule:

```text
Display recommendation results from the backend. Do not recompute ranking in the browser.
```

## Implemented Flow

- 추천 화면: 네이버 Geocoding 기반 출발지 검색, 현재 위치, 연료 타입, 주유량, 연비, 임시 카드 정책 입력.
- 추천 결과: 백엔드 추천 주유소, 비용 분해, 후보 목록, 지도 표시 영역.
- 지도 표시: `VITE_NAVER_MAPS_CLIENT_ID`가 있을 때 네이버 지도 스크립트를 로드한다.
- 지도 fallback: 지도 키가 없거나 스크립트 로딩에 실패해도 추천 결과와 후보 목록은 계속 표시한다.
- 로그인 상태: 저장 차량과 활성 카드가 추천 요청에 반영된다는 안내와 빠른 설정 진입 표시.
- 회원가입/로그인/로그아웃: 세션 기반 API 호출.
- 내 설정: 사용자 정보, 차량 설정, 카드 관리 진입.
- 차량 설정: 연료 타입과 연비 저장.
- 카드 관리: 카드 카탈로그 검색, 후보 확인/수정, 내 카드 저장, 직접 등록, 목록 조회, 삭제.
- 상태 피드백: 위치 권한, 프로필 저장, 카드 검색/저장/삭제, 지도 로딩 실패 상태를 사용자에게 표시.
- 주유소 데이터 갱신: 추천 직전 백엔드 station refresh API를 호출하고, Opinet 키가 없거나 실패하면 저장된 DB 데이터로 계속 계산한다.

## Vehicle Profiles

- Vehicle names are required, trimmed before submission, non-unique, and limited to 40 characters.
- Supported `vehicle_type` values are `sedan`, `suv`, `rv_mpv`, `sports_coupe`, `hatchback`, `wagon`, `convertible`, `pickup`, and `micro_city`.
- `frontend/src/components/vehicles/vehiclePresentation.js` maps each type to a bundled independent SVG card under `frontend/src/assets/vehicles/`, based on the project `car_design.png` reference.
- The UI uses the sedan presentation as the display fallback for an unknown type.
- The vehicle workspace supports list, create, edit, delete, and default-vehicle selection.

## Environment

Only expose frontend-safe public keys here.

```text
VITE_API_BASE_URL=/api/v1
VITE_SEARCH_API_BASE_URL=/search-api
VITE_NAVER_MAPS_CLIENT_ID=naver-maps-javascript-api-key
```

Do not put server-side secrets in Vite environment variables.

During local development, Vite proxies `/api` to Django on port 8000 and
`/search-api` to the optional FastAPI search sidecar on port 8001. If the
sidecar is not running, departure search falls back to the Django geocode API.
Both backend paths use address-first Naver Cloud Maps Geocoding and then
NAVER Developers Local Search when no address result is available. The
browser-side Maps geocoder remains an address fallback and is not a substitute
for Local Search credentials when searching buildings or landmarks.

## Local Verification

```powershell
npm.cmd run build
```

## Naver Map Submission Mapping

This frontend intentionally replaces the PDF's Kakao Map/bank-search domain with
the project domain: **Naver Map based gas-station recommendation**.

| PDF item | Frontend evidence |
| --- | --- |
| F1001 | `VITE_NAVER_MAPS_CLIENT_ID` loads Naver Maps JS only as a public browser key. |
| F1002 | `RecommendationMap.vue` renders the Naver map and centers on the departure point or recommended station. |
| F1003 | The recommendation form supports departure search, current location, map-click departure selection, fuel amount, radius, efficiency, and card conditions. |
| F1004 | Candidate gas stations render as map markers; marker/list selection opens an InfoWindow with station name, address, price, distance, and effective cost. |
| F1011 | The active candidate route is drawn when it has `route_path`; otherwise the backend winner route is kept, and if no routed path exists a non-blocking fallback notice is shown. |

### Screenshot checklist

Capture these screens before submitting the final PDF assignment result:

1. API key/environment variable section and `.gitignore` proving secrets are not committed.
2. Naver map rendered on the recommendation screen.
3. Departure search and recommendation condition controls.
4. Candidate markers plus a marker InfoWindow.
5. Route polyline or route fallback notice.
6. README sections for implemented features, learning, reflections, run commands, and GitLab `10_pjt` submission guidance.
