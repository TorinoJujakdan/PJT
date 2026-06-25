# SmartFuel

Naver 지도/경로와 유가 데이터를 기반으로 주유소와 카드 혜택을 함께 추천하는 서비스입니다.

- **Frontend**: Vue 3 + Vite (`5173`)
- **Backend**: Django REST Framework (`8000`)
- **Search API**: FastAPI sidecar (`8001`, 선택 실행)
- **AI normalization**: Google Gemini API로 카드 원문에서 주유 혜택을 구조화

---

## 처음 실행하기

### 1. 사전 요구사항

- Python 3.10+
- Node.js 18+
- npm

### 2. 저장소 클론

```powershell
git clone <repository-url>
cd PJT
```

### 3. Python 가상환경 및 백엔드 패키지 설치

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
```

### 4. 프론트엔드 패키지 설치

```powershell
cd frontend
npm install
cd ..
```

### 5. 환경변수 파일 설정

`.env.example`을 `.env`로 복사한 뒤 실제 키를 입력합니다.

```powershell
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

> `.env` 파일은 Git에 올리지 않습니다. 실제 API 키는 팀 내 별도 채널로 전달받아 입력하세요.

#### Backend `backend/.env` 필수/권장 값

| 변수 | 용도 | 비고 |
|---|---|---|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | Naver Cloud Maps, Geocoding, Directions | 주유소 위치/경로 계산 |
| `NAVER_LOCAL_CLIENT_ID` / `NAVER_LOCAL_CLIENT_SECRET` | Naver OpenAPI Local Search | 지역 검색 |
| `OPINET_API_KEY` | Opinet 유가 데이터 | 주유소 가격 조회 |
| `GEMINI_API_KEY` | Google Gemini API | 카드 원문에서 주유 혜택 추출 |
| `GEMINI_BASE_URL` | Gemini API base URL | 기본값: `https://generativelanguage.googleapis.com` |
| `GEMINI_MODEL` | Gemini 모델명 | 기본값: `gemini-3.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Gemini 요청 timeout | 기본값: `30` |
| `GEMINI_MAX_OUTPUT_TOKENS` | Gemini 최대 출력 토큰 | 기본값: `2048` |

#### 중요한 AI API 주의사항

- 현재 카드 혜택 정규화는 **GMS가 아니라 Google Gemini API**를 사용합니다.
- 따라서 서비스 실행/카드 재수집/AI 정규화를 하려면 `backend/.env`에 반드시 `GEMINI_API_KEY`를 넣어야 합니다.
- `GEMINI_API_KEY`는 `frontend/.env`에 넣지 마세요. 프론트엔드의 `VITE_` 변수는 브라우저 번들에 노출됩니다.
- `GMS_*` 키가 있더라도 현재 Gemini 정규화 경로의 대체값으로 사용되지 않습니다.
- Selenium으로 네이버 카드 데이터를 다시 수집한 뒤 AI 정규화를 실행하면 Gemini API 토큰이 실제로 사용됩니다.
- 비용/사용량 확인이 필요하면 실행 전 `--limit`을 작게 두고 `--dry-run`으로 먼저 검증하세요.

#### Frontend `frontend/.env` 값

| 변수 | 용도 | 비고 |
|---|---|---|
| `VITE_API_BASE_URL` | 백엔드 API URL | 비우면 기본 프록시 사용 |
| `VITE_SEARCH_API_BASE_URL` | Search API URL | 비우면 기본 프록시 사용 |
| `VITE_NAVER_MAPS_CLIENT_ID` | Naver Maps JavaScript SDK Client ID | 공개 가능한 Client ID만 입력 |

### 6. DB 마이그레이션

```powershell
.venv\Scripts\python backend\manage.py migrate
```

### 7. 초기 카드 데이터 로드

카드 검색 기능은 DB에 적재된 `CardCatalog` 데이터를 조회합니다. 처음 실행할 때는 fixture를 로드하세요.

```powershell
.venv\Scripts\python backend\manage.py loaddata backend\cards\fixtures\card_data.json
```

> 이 단계를 건너뛰면 카드 검색 결과가 비어 보일 수 있습니다.

### 8. 서버 실행

```powershell
# 방법 1: 자동 실행 스크립트
.\start-smartfuel.bat

# 방법 2: 수동 실행
.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
.venv\Scripts\uvicorn search_api.main:app --host 127.0.0.1 --port 8001 --reload
cd frontend
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`에 접속합니다.

---

## 카드 데이터 재수집 및 Gemini 정규화

네이버 카드 URL에서 Selenium으로 다시 수집하고 Gemini로 주유 혜택을 정규화할 수 있습니다.

```powershell
# 저장 없이 1건만 검증
.venv\Scripts\python backend\manage.py ingest_card_search_ai --limit 1 --scroll-count 1 --detail --dry-run

# 실제 저장 실행 예시
.venv\Scripts\python backend\manage.py ingest_card_search_ai --limit 10 --scroll-count 1 --detail
```

주의사항:

- 이 명령은 `GEMINI_API_KEY`가 없으면 Gemini 정규화 단계에서 실패합니다.
- `--dry-run`은 Gemini 호출은 수행하지만 DB에는 저장하지 않습니다.
- `--force`를 붙이면 같은 `source_url`/`raw_hash` 데이터도 다시 저장할 수 있으므로 신중하게 사용하세요.
- 대량 실행 전에는 `--limit 1` 또는 `--limit 10`으로 먼저 확인하세요.

---

## 프로젝트 구조

```text
PJT/
├─ backend/              # Django + FastAPI backend
│  ├─ .env.example       # backend environment template
│  ├─ core/              # Django settings
│  ├─ accounts/          # auth and user profile
│  ├─ vehicles/          # vehicle/fuel profile
│  ├─ cards/             # card catalog and benefit normalization
│  ├─ stations/          # fuel station data and recommendations
│  └─ search_api/        # FastAPI search sidecar
├─ frontend/             # Vue 3 + Vite frontend
│  ├─ .env.example       # frontend environment template
│  └─ src/
├─ docs/                 # API contract JSON and retained project docs
├─ start-smartfuel.bat   # Windows launcher
└─ start-smartfuel.ps1   # launcher implementation
```

---

## 운영/보안 수칙

- `.env` 파일은 절대 Git에 커밋하지 않습니다.
- 브라우저에 노출되는 `VITE_` 변수에는 secret key를 넣지 않습니다.
- `GEMINI_API_KEY`, Naver secret, Opinet key는 모두 `backend/.env`에만 입력합니다.
- `db.sqlite3`는 로컬 개발 DB입니다. 새 clone 후에는 `migrate`와 필요한 fixture load를 다시 실행합니다.
- 카드 검색 프론트엔드는 기존 DB 카탈로그를 검색합니다. 네이버 재수집과 Gemini 정규화는 별도 관리 명령으로 실행합니다.
