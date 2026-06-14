# SmartFuel 기능명세서 v1.1

## 1. 프로젝트 목표

SmartFuel은 사용자의 현재 위치, 차량 연비, 주유량, 보유 카드 혜택을 종합하여 실제 총비용이 가장 낮은 주유소를 추천하는 서비스다.

이번 리팩터링의 목표는 기존 추천 엔진과 아키텍처를 유지하면서 사용자 계정, 차량 프로필, 카드 관리, 프론트 사용자 흐름을 보강하는 것이다.

## 2. 적용 범위

이번 리팩터링 범위는 다음과 같다.

- 신규 `accounts` 앱 추가
- 신규 `vehicles` 앱 추가
- 기존 `cards` 앱 개선
- 기존 `stations` 추천 API 개선
- Vue 프론트 화면 및 사용자 흐름 개선
- API 문서, 테스트, README 갱신

다음 항목은 v1.1 필수 범위에서 제외하고 추후 심화 기능으로 둔다.

- Selenium 기반 범용 크롤링. 단, v1.2부터 사용자가 제공한 허용 도메인에 한해 카드 혜택 후보를 수집하는 통제된 Selenium 수집 기능은 별도 범위로 다룬다.
- LLM 요약 및 데이터 증강
- Opinet 실시간 연동
- 네비게이션 API 기반 실제 경로 거리 연동

## 3. 기능 요구사항

| 번호 | 도메인 | 요구사항명 | 상세 | 우선순위 |
| --- | --- | --- | --- | --- |
| F101 | accounts | 회원가입 | 사용자는 username, password, email을 입력해 가입할 수 있다. | 필수 |
| F102 | accounts | 로그인 | 사용자는 가입한 계정으로 로그인할 수 있다. | 필수 |
| F103 | accounts | 로그아웃 | 로그인 사용자는 세션을 종료할 수 있다. | 필수 |
| F104 | accounts | 현재 사용자 조회 | 프론트는 현재 로그인 상태와 사용자 정보를 조회할 수 있다. | 필수 |
| F105 | accounts | 회원정보 수정 | 사용자는 email, username 등 기본 정보를 수정할 수 있다. | 선택 |
| F106 | vehicles | 차량 프로필 생성/수정 | 사용자는 필수 차량 이름, 차량 유형, 연료 타입, 연비 km/L를 저장할 수 있다. 이름은 앞뒤 공백을 제거하고 40자 이하로 저장하며 중복을 허용한다. | 필수 |
| F107 | vehicles | 차량 프로필 조회 | 추천 요청 전 기본 차량 또는 사용자가 저장한 전체 차량 목록을 불러올 수 있다. | 필수 |
| F108 | recommendations | 저장 차량 기반 추천 | 로그인 사용자가 추천 요청에서 `vehicle`을 생략하면 저장된 차량 프로필을 사용한다. | 필수 |
| F109 | recommendations | 비로그인 추천 유지 | 비로그인 사용자는 기존처럼 요청 본문에 차량 연비를 직접 입력해 추천받을 수 있다. | 필수 |
| F110 | cards | 내 카드 목록 조회 | 로그인 사용자는 본인이 등록한 카드 정책만 조회할 수 있다. | 필수 |
| F111 | cards | 카드 등록 | 사용자는 카드명, 카드사, 할인 방식, 할인값, 브랜드 범위, 월 한도 등을 등록할 수 있다. | 필수 |
| F112 | cards | 카드 삭제 | 사용자는 본인 카드 정책을 비활성화할 수 있다. | 필수 |
| F113 | cards | 카드 수정 | 사용자는 등록한 카드 정책을 수정할 수 있다. | 선택 |
| F114 | frontend | 추천 메인 화면 개선 | 위치, 연료 타입, 주유량, 차량 연비, 카드 적용 여부를 명확히 입력할 수 있어야 한다. | 필수 |
| F115 | frontend | 로그인 상태 UX | 로그인/로그아웃 상태에 따라 네비게이션과 안내 문구가 달라져야 한다. | 필수 |
| F116 | frontend | 차량 설정 화면 | 차량 연료 타입과 연비를 저장/수정하는 화면을 제공한다. | 필수 |
| F117 | frontend | 카드 관리 화면 | 카드 목록, 등록, 삭제 기능을 제공한다. | 필수 |
| F118 | frontend | 추천 결과 설명 개선 | 추천 주유소, 총비용, 주유비, 이동비, 카드 할인, 절감액, 후보 비교를 보기 쉽게 표시한다. | 필수 |

## 4. 비기능 요구사항

| 번호 | 분류 | 요구사항명 | 상세 | 우선순위 |
| --- | --- | --- | --- | --- |
| NF101 | 구조 | 기존 아키텍처 유지 | `stations/services.py`의 추천 계산 구조는 유지하고 필요한 입력 확장만 수행한다. | 필수 |
| NF102 | 보안 | 인증 필요 API 보호 | 차량/카드/내 정보 API는 로그인 사용자만 접근 가능해야 한다. | 필수 |
| NF103 | 검증 | Serializer 기반 입력 검증 | 모든 API 입력값은 DRF Serializer에서 검증한다. | 필수 |
| NF104 | 테스트 | 회귀 테스트 유지 | 기존 추천 테스트가 계속 통과해야 한다. | 필수 |
| NF105 | 문서 | API 계약 갱신 | `docs/02_api_blueprint.json` 또는 분리 문서에 신규 API를 반영한다. | 필수 |
| NF106 | UX | 프론트 계산 금지 | 프론트는 추천 순위를 재계산하지 않고 백엔드 응답만 표시한다. | 필수 |

## 5. 신규 및 개선 API 명세

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/accounts/signup/` | optional | 회원가입 |
| POST | `/api/v1/accounts/login/` | optional | 로그인 |
| POST | `/api/v1/accounts/logout/` | required | 로그아웃 |
| GET | `/api/v1/accounts/me/` | optional | 현재 사용자 조회 |
| PATCH | `/api/v1/accounts/me/` | required | 회원정보 수정 |
| GET | `/api/v1/me/vehicle/` | required | 내 차량 프로필 조회 |
| PUT | `/api/v1/me/vehicle/` | required | 내 차량 프로필 생성/수정 |
| GET | `/api/v1/me/vehicles/` | required | 내 차량 목록 조회 |
| POST | `/api/v1/me/vehicles/` | required | 내 차량 추가 |
| PATCH | `/api/v1/me/vehicles/{vehicle_id}/` | required | 내 차량 일부 수정 |
| PUT | `/api/v1/me/vehicles/{vehicle_id}/` | required | 내 차량 전체 수정 |
| DELETE | `/api/v1/me/vehicles/{vehicle_id}/` | required | 내 차량 삭제 |
| POST | `/api/v1/me/vehicles/{vehicle_id}/set-default/` | required | 기본 차량 지정 |
| GET | `/api/v1/me/cards/` | required | 내 카드 목록 조회 |
| POST | `/api/v1/me/cards/` | required | 카드 등록 |
| PATCH | `/api/v1/me/cards/{card_id}/` | required | 카드 수정 |
| DELETE | `/api/v1/me/cards/{card_id}/` | required | 카드 삭제 |
| POST | `/api/v1/recommendations/quote/` | optional | 추천 요청. 로그인 사용자는 저장 차량/카드를 활용할 수 있다. |

## 6. 추천 API 개선 규칙

`POST /api/v1/recommendations/quote/`는 다음 규칙을 따른다.

- 비로그인 사용자는 `vehicle.fuel_efficiency_kmpl`을 반드시 전달해야 한다.
- 로그인 사용자가 요청에 `vehicle`을 전달하면 요청 값을 우선 사용한다.
- 로그인 사용자가 요청에 `vehicle`을 전달하지 않으면 저장된 `VehicleProfile`을 사용한다.
- 로그인 사용자에게 저장 차량이 없으면 `MISSING_VEHICLE_EFFICIENCY`를 반환한다.
- 로그인 사용자의 활성 카드 정책은 자동으로 추천 계산에 포함한다.
- 요청 본문에 전달된 임시 카드 정책도 기존처럼 계산에 포함할 수 있다.
- 추천 계산식과 정렬 기준은 기존 `effective_total_cost` 기준을 유지한다.

## 7. 데이터 모델

### 7.1 신규 `VehicleProfile`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `user` | ForeignKey | Django User와 연결 |
| `name` | CharField(40) | 필수 차량 이름. 앞뒤 공백 제거, 40자 이하, 중복 허용 |
| `vehicle_type` | CharField | `sedan`, `suv`, `rv_mpv`, `sports_coupe`, `hatchback`, `wagon`, `convertible`, `pickup`, `micro_city` 중 하나 |
| `fuel_type` | CharField | `gasoline`, `diesel`, `lpg`, `premium_gasoline` 중 하나 |
| `fuel_efficiency_kmpl` | DecimalField | 차량 연비. 허용 범위는 1.0 이상 50.0 이하 |
| `is_default` | BooleanField | 기본 차량 여부 |
| `created_at` | DateTimeField | 생성 시각 |
| `updated_at` | DateTimeField | 수정 시각 |

### 7.2 기존 `CardPolicy`

`CardPolicy`는 현재 모델을 유지한다.

이번 단계에서는 별도 `UserCard` 모델을 만들지 않고, 현재처럼 `CardPolicy.owner` 구조를 유지한다. 필요한 변경은 카드 수정 API 추가와 검증 보강으로 제한한다.

## 8. 프론트 화면 구성

| 화면 | 설명 |
| --- | --- |
| `RecommendView` | 추천 메인 화면. 현재 구현을 유지하면서 UX를 정리한다. |
| `LoginView` | 로그인 화면 |
| `SignupView` | 회원가입 화면 |
| `ProfileView` | 내 정보, 차량/카드 관리 진입점 |
| `VehicleView` | 차량 이름, 차량 유형, 연료 타입, 연비를 등록/수정하고 기본 차량을 선택하는 화면 |
| `CardsView` | 카드 목록/등록/수정/삭제 화면 |
| 공통 네비게이션 | 로그인 상태에 따라 메뉴와 안내 문구를 변경한다. |

## 9. 완료 기준

이번 리팩터링은 다음 조건을 만족하면 완료로 본다.

- 기존 백엔드 테스트가 모두 통과한다.
- 신규 accounts, vehicles, cards, recommendation 테스트가 추가된다.
- 로그인 사용자가 차량 정보를 저장하고, 추천 요청에서 차량 입력 없이 추천받을 수 있다.
- 로그인 사용자의 저장 카드가 추천 결과에 자동 반영된다.
- 비로그인 사용자의 기존 추천 흐름은 깨지지 않는다.
- 프론트에서 회원가입, 로그인, 차량 저장, 카드 등록, 추천 요청 흐름이 가능하다.
- 프론트 빌드가 통과한다.
- API 문서와 README가 신규 기능을 반영한다.

## 10. 권장 구현 순서

1. `accounts` 앱 추가
2. `vehicles` 앱 추가
3. 추천 API에서 저장 차량 fallback 적용
4. 카드 수정 API 추가
5. accounts, vehicles, cards API 테스트 추가
6. 프론트 라우팅과 로그인 상태 관리 추가
7. 차량/카드 관리 화면 추가
8. 추천 화면 UX 정리
9. 문서와 README 갱신
10. 전체 테스트와 빌드 검증

## 10.1 차량 이름/유형 및 초기화 구현 규칙

- `VehicleProfile.name`은 필수이며 저장 전에 앞뒤 공백을 제거한다.
- 차량 이름은 최대 40자이고 고유값이 아니다. 같은 사용자를 포함해 중복 이름을 허용한다.
- `VehicleProfile.vehicle_type`은 `sedan`, `suv`, `rv_mpv`, `sports_coupe`, `hatchback`, `wagon`, `convertible`, `pickup`, `micro_city` 중 하나여야 한다.
- 마이그레이션 `vehicles.0005_reset_profiles_expand_vehicle_types`은 기존 차량 프로필을 삭제한 뒤 9종 Django field choices 계약을 적용한다.
- 프론트엔드는 각 차량 유형을 `car_design.png`를 참고해 제작한 독립 정적 SVG 카드에 매핑한다. 외부 이미지 URL이나 런타임 이미지 검색을 사용하지 않는다.
- 알 수 없는 차량 유형의 표시 fallback은 `sedan` 실루엣이다.
- 마이그레이션 `vehicles.0003_reset_profiles_add_name_vehicle_type`은 기존 `VehicleProfile` 행만 삭제한 뒤 필수 필드를 추가한다.
- 위 초기화는 사용자, 카드, 주유소, 유가 데이터에 영향을 주지 않는다.

---

# v1.2 업그레이드 확장 명세

## 11. v1.2 목표

v1.2의 목표는 SmartFuel을 단순 CRUD와 표 형태 추천 화면에서 벗어나, 실제 지도 기반 탐색과 카드 혜택 자동 선택을 지원하는 상용 서비스형 사용자 경험으로 확장하는 것이다.

이번 확장은 하네스 엔지니어링 규칙을 엄격히 따른다.

- 추천 순위 계산은 계속 `backend/stations/services.py`에서 수행한다.
- 프론트엔드는 네이버 지도와 추천 결과를 표시하지만 추천 순위를 재계산하지 않는다.
- 외부 지도 API, 카드 혜택 수집, 카드 이미지 수집은 추천 계산과 분리한다.
- Selenium 수집 데이터는 사용자가 확인하거나 관리자가 검증하기 전까지 추천 랭킹에 사용하지 않는다.
- 구현 전에 관련 API 계약 chunk를 먼저 추가하거나 갱신한다.

## 12. v1.2 추가 기능 요구사항

| 번호 | 도메인 | 요구사항명 | 상세 | 우선순위 |
| --- | --- | --- | --- | --- |
| F201 | maps | 네이버 지도 기반 추천 화면 | 프론트엔드는 네이버 지도 JavaScript API를 사용해 사용자 위치와 추천 후보 주유소를 지도에 표시한다. 공식 문서 기준으로 Dynamic Map 사용 가능 여부와 인증 키 설정을 먼저 확인한다. | 필수 |
| F202 | maps | 추천 주유소 마커 표시 | 추천 API 응답의 후보 주유소 좌표를 사용해 지도 위에 마커를 표시한다. 최종 추천 주유소, 후보 주유소, 선택된 주유소는 시각적으로 구분한다. | 필수 |
| F203 | maps | 지도-목록 연동 | 사용자가 지도 마커를 선택하면 후보 목록의 같은 주유소가 강조되고, 목록 항목을 선택하면 지도 중심과 활성 마커가 갱신된다. | 필수 |
| F204 | maps | 지도 장애 fallback | 네이버 지도 스크립트 로딩 실패, API 키 누락, quota 초과, 네트워크 장애가 발생해도 추천 목록과 비용 비교는 계속 사용할 수 있어야 한다. | 필수 |
| F205 | cards | 카드 카탈로그 조회 | 사용자는 직접 할인율을 입력하지 않고, 수집 또는 검증된 카드 카탈로그에서 본인의 카드를 검색하고 선택할 수 있다. | 필수 |
| F206 | cards | 카드 선택 시 혜택 자동 입력 | 사용자가 카드 카탈로그에서 카드를 선택하면 카드명, 카드사, 카드 이미지, 할인 방식, 할인값, 브랜드 범위, 한도 정보가 카드 정책 입력 폼에 자동 채워진다. | 필수 |
| F207 | cards | 카드 실물 이미지 표시 | 카드 카탈로그와 내 카드 목록은 카드 이미지가 있을 경우 실물 카드 이미지를 표시한다. 이미지가 없거나 로딩 실패 시 로컬 placeholder를 표시한다. | 필수 |
| F208 | cards | Selenium 카드 혜택 후보 수집 | 사용자가 제공한 허용 도메인에서 Selenium을 통해 공개 카드 혜택 후보 데이터를 수집할 수 있다. 수집은 오프라인 관리 명령 또는 별도 ingestion 작업으로만 수행하고, 사용자 요청 처리 경로에서는 실행하지 않는다. | 선택 |
| F209 | cards | 수집 후보 검증 워크플로우 | Selenium으로 수집한 카드 혜택은 `unverified` 상태로 저장하며, 사용자가 선택 후 확인하거나 관리자가 검증하기 전까지 추천 계산에 반영하지 않는다. | 필수 |
| F210 | frontend | 사용자 맞춤형 앱 셸 | 로그인 사용자에게 저장 차량, 등록 카드, 최근 추천 조건, 추천 실행 CTA가 한 화면에서 연결되는 앱 셸을 제공한다. 저장/수정 후 무조건 메인 화면으로 돌아가는 흐름을 줄인다. | 필수 |
| F211 | frontend | 작업 맥락 유지 | 차량 저장, 카드 등록, 추천 실행 후 사용자가 하던 작업 맥락을 유지한다. 예: 카드 선택 후 추천 화면의 카드 적용 상태가 즉시 갱신된다. | 필수 |
| F212 | frontend | 상용 수준 상태 피드백 | 모든 저장/삭제/지도 로딩/카드 수집/추천 요청에 loading, success, empty, error 상태를 제공한다. 오류는 가능한 한 필드 단위로 표시한다. | 필수 |

## 13. v1.2 비기능 요구사항

| 번호 | 분류 | 요구사항명 | 상세 | 우선순위 |
| --- | --- | --- | --- | --- |
| NF201 | 계약 | 지도 표시와 추천 계산 분리 | 지도는 추천 결과를 표시하는 presentation layer다. 지도 위 거리 또는 마커 순서로 추천 순위를 재계산하면 안 된다. | 필수 |
| NF202 | 외부 API | 네이버 지도 키 관리 | 네이버 지도 API 키는 환경 변수로 관리한다. 프론트 번들에 노출되는 키는 네이버 지도 JavaScript API 용도에 한정하고, 서버용 Secret은 클라이언트에 노출하지 않는다. | 필수 |
| NF203 | 외부 API | 지도 장애 허용 | 지도 API 실패가 추천 API 실패로 이어지면 안 된다. 추천 결과는 지도 없이도 확인 가능해야 한다. | 필수 |
| NF204 | 수집 | 도메인 허용 목록 | Selenium 수집은 사용자가 명시한 도메인만 대상으로 한다. 도메인이 제공되기 전에는 구현자가 임의 URL을 선택하지 않는다. | 필수 |
| NF205 | 수집 | 접근 통제 준수 | 로그인 우회, 유료/비공개 페이지 접근, CAPTCHA 우회, anti-bot 우회, 과도한 요청, 결제정보 수집은 금지한다. | 필수 |
| NF206 | 수집 | 원천 메타데이터 보존 | 수집 데이터는 `source_url`, `source_title`, `collected_at`, `provider`, `raw_summary`, `confidence`를 보존해야 한다. | 필수 |
| NF207 | 데이터 신뢰 | 미검증 데이터 격리 | `unverified` 카드 혜택은 추천 계산에 사용하지 않는다. 사용자가 명시적으로 확인한 경우 `user_confirmed`, 운영자가 검증한 경우 `admin_verified`로 전환한다. | 필수 |
| NF208 | UX | 접근성과 반응형 | 지도/목록/카드 UI는 모바일과 데스크톱에서 모두 사용할 수 있어야 하며, 키보드 포커스와 스크린리더 대체 텍스트를 제공한다. | 필수 |
| NF209 | QA | 브라우저 검증 | 지도 로딩, 마커 표시, 카드 선택 자동 입력, 저장 후 추천 반영은 브라우저 smoke test로 검증한다. | 필수 |

## 14. v1.2 API 계약 확장 방향

구현 전 다음 endpoint chunk를 추가하거나 갱신한다.

| 문서 | 목적 |
| --- | --- |
| `docs/api_contracts/recommendations_quote.json` | 추천 응답의 주유소 좌표, 지도 표시용 후보 메타데이터, 선택 카드 이미지 필드가 명확한지 확인한다. |
| `docs/api_contracts/cards_policies.json` | 내 카드 저장 API가 카탈로그에서 선택한 카드 혜택을 저장할 수 있는지 확인한다. |
| `docs/api_contracts/cards_catalog.json` | 카드 카탈로그 검색, 후보 조회, 사용자 확인, 내 카드로 저장하는 API 계약을 정의한다. |
| `docs/api_contracts/cards_ingestion.json` | Selenium 수집 작업 요청, 허용 도메인, 수집 결과 상태, 오류 코드를 정의한다. 운영/개발용 endpoint로 둘지 management command로 둘지는 Architect가 먼저 결정한다. |

권장 신규 API는 다음과 같다.

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/v1/cards/catalog/` | required | 검증된 카드 카탈로그 검색. `query`, `issuer_name`, `brand_scope` 필터를 지원한다. |
| GET | `/api/v1/cards/catalog/{catalog_card_id}/` | required | 카드 이미지, 혜택 조건, 출처, 검증 상태를 포함한 상세 조회. |
| POST | `/api/v1/me/cards/from-catalog/` | required | 카탈로그 카드 혜택을 사용자가 확인한 뒤 내 카드 정책으로 저장한다. |
| POST | `/api/v1/cards/ingestion/jobs/` | admin 또는 local-only | 허용 도메인 기반 Selenium 수집 작업을 생성한다. 운영 노출 여부는 별도 보안 검토 후 결정한다. |
| GET | `/api/v1/cards/ingestion/jobs/{job_id}/` | admin 또는 local-only | 수집 작업 상태와 수집 후보 개수를 조회한다. |

## 15. v1.2 데이터 모델 확장 방향

현재 `CardPolicy.owner` 기반 구조는 유지한다. 단, 카드 카탈로그와 사용자 보유 카드를 분리하기 위해 다음 모델 추가를 검토한다.

### 15.1 신규 `CardCatalog`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `card_name` | CharField | 카드명 |
| `issuer_name` | CharField | 카드사 |
| `discount_type` | CharField | `per_liter`, `percentage`, `fixed_amount` |
| `discount_value` | DecimalField | 할인값 |
| `brand_scope` | CharField | 적용 주유 브랜드 |
| `min_payment_amount` | PositiveIntegerField nullable | 최소 결제금액 |
| `max_discount_amount` | PositiveIntegerField nullable | 건별 최대 할인 |
| `monthly_discount_limit` | PositiveIntegerField nullable | 월 할인 한도 |
| `card_image_url` | URLField blank | 카드 이미지 URL |
| `source_url` | URLField blank | 혜택 출처 URL |
| `source_title` | CharField blank | 출처 제목 |
| `source_type` | CharField | `issuer`, `naver_search`, `manual_seed`, `selenium` |
| `verification_status` | CharField | `unverified`, `user_confirmed`, `admin_verified` |
| `confidence` | DecimalField nullable | 수집/파싱 신뢰도 |
| `collected_at` | DateTimeField nullable | 수집 시각 |

### 15.2 `CardPolicy` 연계

`CardPolicy`는 사용자가 실제 추천에 사용할 보유 카드 정책이다. 카탈로그에서 저장한 경우 `catalog_card` nullable ForeignKey를 둘 수 있다.

추천 계산에 사용할 수 있는 정책은 다음 중 하나다.

- 사용자가 직접 입력한 `manual` 정책
- 카탈로그에서 선택 후 사용자가 확인한 `user_confirmed` 정책
- 운영자가 검증한 `admin_verified` 정책

## 16. 네이버 지도 UI 설계 원칙

네이버 지도 JavaScript API v3를 기준으로 지도 UI를 설계한다. API 인증 방식, Dynamic Map 사용 설정, 클라이언트 키 파라미터는 구현 직전에 공식 문서를 다시 확인한다.

참고 공식 문서:

- NAVER Maps API v3 기술문서: https://navermaps.github.io/maps.js.ncp/docs/
- Client ID 발급 및 `ncpKeyId` 변경 안내: https://navermaps.github.io/maps.js.ncp/docs/tutorial-1-Getting-Client-ID.html

지도 UI는 다음 상태를 지원한다.

- `loading`: 지도 스크립트 로딩 중
- `ready`: 지도 표시 가능
- `degraded`: 지도는 실패했지만 추천 목록은 사용 가능
- `empty`: 추천 후보 없음
- `selected`: 지도 마커와 후보 목록이 같은 주유소를 가리킴

지도 마커는 다음 정보를 표시한다.

- 최종 추천 여부
- 주유소명
- 브랜드
- 리터당 가격
- 거리
- 예상 총비용
- 적용 카드 또는 할인 없음

## 17. Selenium 카드 혜택 수집 원칙

Selenium은 공개 카드 혜택 후보를 수집하기 위한 보조 도구다. 추천 계산, 사용자 요청 처리, 실시간 화면 렌더링 경로에 직접 넣지 않는다.

수집 작업은 다음 절차로만 진행한다.

1. 사용자가 수집 대상 도메인을 제공한다.
2. Architect가 도메인, 수집 목적, 수집 필드, 저장 모델, API 계약을 문서에 기록한다.
3. DevOps 또는 Backend Coder가 robots.txt, 약관, 접근 가능 여부, 인증 필요 여부를 확인한다.
4. Backend Coder가 domain allowlist 기반 수집기를 구현한다.
5. 수집 결과는 `unverified`로 저장한다.
6. Frontend Coder는 사용자가 후보를 확인/수정/저장하는 UI를 구현한다.
7. QA Agent는 수집 실패, 빈 결과, 이미지 실패, 중복 카드, 잘못된 할인값을 검증한다.

수집 금지 항목:

- 카드 번호, CVC, 비밀번호, 주민등록번호, 결제 인증 정보
- 로그인 우회가 필요한 비공개 혜택 페이지
- CAPTCHA 또는 anti-bot 우회
- 약관상 자동화 접근이 금지된 페이지
- 출처가 불명확한 이미지의 무단 저장

## 18. 사용자 맞춤 UI 방향

현재처럼 작업 후 메인 화면으로 되돌리는 구조를 줄이고, 사용자가 하던 흐름 안에서 다음 행동을 이어갈 수 있게 한다.

권장 화면 구조:

- 상단 또는 좌측 앱 셸: 추천, 지도, 차량, 카드, 계정 상태를 일관되게 이동
- 추천 화면: 지도와 후보 목록을 같은 화면에서 표시
- 차량 패널: 추천 화면 안에서 저장 차량을 빠르게 확인하고 수정 화면으로 진입
- 카드 패널: 저장 카드와 카탈로그 선택을 같은 흐름에서 제공
- 카드 선택 drawer 또는 modal: 카드 검색, 이미지 확인, 혜택 미리보기, 내 카드로 저장
- 저장 후 동작: 이전 작업 위치로 복귀하고 추천 조건을 즉시 갱신

UI 완료 조건:

- 사용자가 로그인 후 추천을 실행하기까지 필요한 단계가 명확하다.
- 저장 차량과 저장 카드가 추천 조건에 어떻게 반영되는지 화면에서 확인할 수 있다.
- 지도 없이도 추천 결과를 이해할 수 있다.
- 지도와 목록이 서로 같은 후보를 가리킨다.
- 저장/삭제/선택 실패 시 복구 가능한 안내를 제공한다.

## 19. v1.2 구현 통제 절차

v1.2 코딩은 다음 순서로만 진행한다.

1. Architect: `docs/api_contracts/cards_catalog.json`, `docs/api_contracts/cards_ingestion.json` 추가 여부와 `recommendations_quote.json` 변경 여부를 결정한다.
2. Architect: 네이버 지도 키, 지도 표시 필드, 카드 카탈로그 필드, Selenium 허용 도메인 정책을 문서에 확정한다.
3. Backend Coder: 카드 카탈로그 모델/API를 구현하고 테스트를 추가한다.
4. Backend Coder: Selenium 수집은 허용 도메인이 제공된 뒤 별도 slice로 구현한다.
5. Frontend Coder: 네이버 지도 컴포넌트를 추천 결과 표시용으로 구현한다. 추천 계산 로직은 넣지 않는다.
6. Frontend Coder: 카드 카탈로그 선택 UI와 자동 입력 UI를 구현한다.
7. Frontend Coder: 앱 셸과 작업 맥락 유지 UX를 구현한다.
8. QA Agent: API 계약, 저장/추천 회귀, 지도 fallback, 카드 자동 입력, 브라우저 smoke를 검증한다.
9. QA Agent: 결과를 `docs/05_test_reports.md`에 기록한다.

각 slice는 다음 게이트를 통과해야 다음 slice로 넘어간다.

- 관련 API chunk가 존재하고 구현과 일치한다.
- 백엔드 테스트가 통과한다.
- 프론트 빌드가 통과한다.
- 외부 API 또는 Selenium 실패 시 fallback이 동작한다.
- 미검증 카드 혜택이 추천 계산에 사용되지 않는다.
- QA 결과가 기록된다.

## 20. v1.2 권장 구현 순서

1. CSRF 기반 저장 실패 안정화
2. 한글 깨짐, 폼 검증, 저장/삭제 상태 피드백 개선
3. 추천 응답의 지도 표시 필드 계약 확인
4. 네이버 지도 API 키 환경 변수와 지도 컴포넌트 추가
5. 추천 주유소 마커와 후보 목록 연동
6. 카드 카탈로그 API 계약 추가
7. 카드 카탈로그 모델/API/테스트 구현
8. 카드 검색/선택/자동 입력 UI 구현
9. 사용자가 제공한 도메인 기반 Selenium 수집 slice 설계
10. Selenium 수집기와 미검증 후보 확인 UI 구현
11. 앱 셸과 사용자 맞춤 흐름 정리
12. 전체 회귀 테스트, 브라우저 검증, 문서 갱신
