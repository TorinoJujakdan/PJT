# 📐 SmartFuel 시스템 개선 구현 설계도

이 설계도는 **1) 출발 위치 검색 고도화**, **2) 오피넷 유가 자동 동기화**, **3) 카드 혜택 동적 수집 및 자동 검증**이라는 세 가지 핵심 과제를 수행하기 위해 설계되고 프로젝트에 반영되었습니다.

---

## 1️⃣ 출발 위치 검색 고도화 (Backend Geocoding Proxy + Frontend Debounce)

### 📌 설계 목적
* 프론트엔드 코드에 네이버/카카오 API 키를 노출하는 보안 리스크를 완전히 제거합니다.
* 사용자가 검색어를 입력할 때마다 API 호출이 무분별하게 발생하지 않도록 **300ms 디바운싱(Debounce)**을 적용합니다.
* 운영 UX에서 로컬 더미 프리셋이 검색 결과처럼 노출되지 않도록 네이버 Geocoding 결과와 실패 상태를 명확히 분리합니다.

### 🛠️ 세부 설계 내용
* **API 계약(Contract-First)**: 
  * `docs/api_contracts/locations_geocode.json`에 엔드포인트 규격 선 정의
  * `GET /api/v1/stations/geocode/?query={검색어}` 엔드포인트 등록
  * `GET /api/v1/stations/reverse-geocode/?latitude={위도}&longitude={경도}` 엔드포인트 등록
* **백엔드 프록시 (Geocoding Proxy)**:
  * 외부 네이버 지도 API에 안전하게 통신 및 토큰 암호화 처리.
  * API Key가 없는 환경에서는 빈 결과와 `meta.status=unavailable`을 반환해 더미 위치를 실제 검색 결과로 오인하지 않도록 처리.
* **프론트엔드 검색 고도화**:
  * `LocationControl.vue` 내에 `300ms 디바운스` 로직을 구축해 검색어가 완성되었을 때 백엔드 프록시를 호출.
  * 브라우저 현재 위치와 지도 클릭 좌표는 Reverse Geocoding으로 주소 라벨을 확정.

---

## 2️⃣ 오피넷 유가 정보 동기화 자동화 (APScheduler 크론 스케줄링)

### 📌 설계 목적
* 오피넷 유가 데이터가 매일 오후 5시에 업로드되는 특징에 맞추어 하루 2회(05:01 AM, 17:01 PM)에 걸쳐 데이터를 실시간에 가깝게 가져옵니다.
* Django의 핫 리로딩 프로세스(StatReloader)나 다중 프로세스 가동 시 동일 스케줄러가 여러 번 가동되어 데이터가 중복 갱신되거나 SQLite가 Lock 걸려 데드락이 발생하는 현상을 원천 방지합니다.

### 🛠️ 세부 설계 내용
* **단일 서버 전용 백그라운드 스케줄러**:
  * `django-apscheduler` 라이브러리를 도입하여 데이터베이스와 연동해 단일 인스턴스에서 안전하게 잡(Job)이 관리되도록 설계.
  * 스케줄 크론 표현식: `05:01 AM (cron: 1 5 * * *)`, `17:01 PM (cron: 1 17 * * *)` 등록.
* **SQLite 데드락 방지 프로세스 가드**:
  * Django 초기화 `apps.py` 내부 `ready()` 메서드에서 오토 리로더의 부모 프로세스 중복 구동을 걸러내는 `os.environ.get('RUN_MAIN') == 'true'` 조건 검증 적용.
  * `manage.py test` 및 `migrate` 같은 다른 백그라운드 마이그레이션/테스트 커맨드 실행 시 스케줄러가 임의로 실행되지 않도록 커맨드 라인 인자 필터링 가드 설정.

---

## 3️⃣ 카드 혜택 데이터 수집 및 자동 검증 자동화 (Selenium + Auto-Verification)

### 📌 설계 목적
* 네이버 카드 검색 화면에서 "더보기" 버튼을 클릭하지 않으면 첫 화면의 제한된 혜택 카드만 수집되는 한계를 극복합니다.
* 크롤러가 수집한 미검증 카드 중 정확도가 높은 카드 데이터를 휴먼 인터벤션(수동 관리자 검증) 없이 시스템이 능동적으로 판단하여 즉각 자동 승인(`ADMIN_VERIFIED`) 처리합니다.

### 🛠️ 세부 설계 내용
* **Selenium 더보기(More) 버튼 구동 자동화**:
  * 크롤링 뷰포트 내 스크롤을 내리며, WebDriverWait을 통해 동적으로 로딩되는 **더보기** 요소를 Xpath `text()` 쿼리 및 클래스 셀렉터(`.btn_more`)를 활용해 안정적으로 탐색.
  * 웹 페이지가 깨지거나 루프에 빠지는 것을 방지하기 위해 최대 5회까지만 클릭을 시도하도록 임계치 설정.
* **Auto-Verification 비즈니스 룰 엔진**:
  * 크롤링하여 획득한 카드 모델 데이터에 **Confidence Score (신뢰도 점수)** 계산 로직 적용.
  * **자동 검증 조건**:
    1. 신뢰도(Confidence Score) 점수가 $\ge 0.85$ 이상
    2. 카드 명칭(`card_name`) 및 카드사명(`issuer_name`)이 누락 없이 존재할 것
    3. 실질적인 할인 혜택 수치(`discount_value`)가 0보다 클 것
  * 이 세 가지 조건을 완벽히 충족하는 데이터는 관리자 승인 대기(`UNVERIFIED`) 상태가 아닌 즉시 노출 가능한 **검증 완료(`ADMIN_VERIFIED`)** 상태로 SQLite DB에 적재.

---

## 📂 변경 및 추가된 주요 파일 아키텍처

```
📂 pjtworkspace
 ┣ 📂 docs
 ┃ ┣ 📄 02_api_blueprint.json            # [MODIFY] 지오코딩 API 계약 스펙 명세서 등록
 ┃ ┣ 📄 implementation_blueprint.md      # [NEW] 본 개선 설계도 문서
 ┃ ┗ 📂 api_contracts
 ┃ ┃ ┗ 📄 locations_geocode.json         # [NEW] /api/v1/stations/geocode/ 세부 명세서 계약 생성
 ┣ 📂 backend
 ┃ ┣ 📂 core
 ┃ ┃ ┗ 📄 settings.py                     # [MODIFY] django_apscheduler 앱 추가 및 DB 설정
 ┃ ┣ 📂 stations
 ┃ ┃ ┣ 📄 urls.py                         # [MODIFY] geocode API 엔드포인트 매핑
 ┃ ┃ ┣ 📄 views.py                        # [NEW] GeocodeAPIView 구현
 ┃ ┃ ┣ 📄 geocoding_service.py            # [NEW] Naver Geocoding/Reverse Geocoding 프록시 서비스
 ┃ ┃ ┣ 📄 scheduler.py                    # [NEW] APScheduler cron 2회 동기화 스케줄 구축
 ┃ ┃ ┣ 📄 apps.py                         # [MODIFY] 중복 초기화 방지 및 SQLite 데드락 방지 가드 적용
 ┃ ┃ ┗ 📄 tests_additions.py              # [NEW] 지오코딩 API + 주유소 refresh + 자동 검증 테스트
 ┃ ┣ 📂 cards
 ┃ ┃ ┗ 📄 selenium_ingestion.py           # [MODIFY] Selenium 더보기 클릭 자동화 + Auto-Verification 조건 구현
 ┗ 📂 frontend
 ┃ ┗ 📂 src
 ┃ ┃ ┗ 📂 components
 ┃ ┃ ┃ ┗ 📄 LocationControl.vue          # [MODIFY] 300ms 디바운스 및 지오코딩 API 연동
```
