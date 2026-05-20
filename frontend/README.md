# SmartFuel Frontend

Vue 3 + Vite frontend for SmartFuel.

The frontend consumes the API contract in `docs/02_api_blueprint.json`.

Frontend rule:

```text
Display recommendation results from the backend. Do not recompute ranking in the browser.
```

## Implemented Flow

- 추천 화면: 위치, 연료 타입, 주유량, 연비, 임시 카드 정책 입력.
- 추천 결과: 백엔드 추천 주유소, 비용 분해, 후보 목록, 지도 표시 영역.
- 지도 표시: `VITE_NAVER_MAPS_CLIENT_ID`가 있을 때 네이버 지도 스크립트를 로드한다.
- 지도 fallback: 지도 키가 없거나 스크립트 로딩에 실패해도 추천 결과와 후보 목록은 계속 표시한다.
- 로그인 상태: 저장 차량과 활성 카드가 추천 요청에 반영된다는 안내와 빠른 설정 진입 표시.
- 회원가입/로그인/로그아웃: 세션 기반 API 호출.
- 내 설정: 사용자 정보, 차량 설정, 카드 관리 진입.
- 차량 설정: 연료 타입과 연비 저장.
- 카드 관리: 카드 카탈로그 검색, 후보 확인/수정, 내 카드 저장, 직접 등록, 목록 조회, 삭제.
- 상태 피드백: 위치 권한, 프로필 저장, 카드 검색/저장/삭제, 지도 로딩 실패 상태를 사용자에게 표시.

## Environment

Only expose frontend-safe public keys here.

```text
VITE_API_BASE_URL=/api/v1
VITE_NAVER_MAPS_CLIENT_ID=naver-maps-javascript-api-key
```

Do not put server-side secrets in Vite environment variables.

## Local Verification

```powershell
npm.cmd run build
```
