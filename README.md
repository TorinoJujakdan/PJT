# SmartFuel

네이버 지도 기반 주유소 추천 서비스

- **Frontend**: Vue 3 + Vite (port 5173)
- **Backend**: Django REST Framework (port 8000)
- **Search API**: FastAPI sidecar (port 8001, 선택)

---

## 🚀 처음 시작하기 (clone 후 셋업)

### 사전 요구사항

- Python 3.10+
- Node.js 18+
- npm

### 1단계: 저장소 클론

```bash
git clone <repository-url>
cd PJT
```

### 2단계: Python 가상환경 생성 & 패키지 설치

```powershell
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
```

### 3단계: 프론트엔드 패키지 설치

```powershell
cd frontend
npm install
cd ..
```

### 4단계: 환경변수 파일 설정 ⚠️

**`.env.example` 파일을 `.env`로 복사**한 뒤 팀원에게 전달받은 실제 API 키를 입력하세요.

```powershell
# 백엔드
copy backend\.env.example backend\.env

# 프론트엔드
copy frontend\.env.example frontend\.env
```

> **주의**: `.env` 파일은 `.gitignore`에 포함되어 Git에 올라가지 않습니다.
> API 키는 팀원에게 별도로 전달받으세요 (카톡, DM 등).

필요한 API 키 목록:

| 키 | 발급처 | 용도 |
|---|---|---|
| `NAVER_CLIENT_ID` / `SECRET` | [네이버 클라우드 플랫폼](https://www.ncloud.com/) | 지도, 지오코딩, 경로 |
| `NAVER_LOCAL_CLIENT_ID` / `SECRET` | [네이버 개발자 센터](https://developers.naver.com/) | 지역 검색 |
| `OPINET_API_KEY` | [오피넷](https://www.opinet.co.kr/) | 주유소 유가 데이터 |
| `VITE_NAVER_MAPS_CLIENT_ID` | 네이버 클라우드 플랫폼 (위 Client ID와 동일) | 브라우저 지도 SDK |

### 5단계: DB 마이그레이션

```powershell
.venv\Scripts\python backend\manage.py migrate
```

### 6단계: 서버 실행

```powershell
# 방법 1: 원클릭 실행 (권장)
start-smartfuel.bat

# 방법 2: 수동 실행 (각각 별도 터미널)
.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
.venv\Scripts\uvicorn search_api.main:app --host 127.0.0.1 --port 8001 --reload
cd frontend && npm run dev
```

실행 후 브라우저에서 http://127.0.0.1:5173 접속

---

## 📁 프로젝트 구조

```
PJT/
├── backend/              # Django + FastAPI 백엔드
│   ├── .env.example      # ← 환경변수 템플릿
│   ├── core/             # Django 프로젝트 설정
│   ├── accounts/         # 인증, 사용자 프로필
│   ├── vehicles/         # 차량 연비 관리
│   ├── cards/            # 카드 할인 정책
│   ├── stations/         # 주유소 데이터, 추천
│   └── search_api/       # FastAPI 검색 사이드카
├── frontend/             # Vue 3 + Vite 프론트엔드
│   ├── .env.example      # ← 환경변수 템플릿
│   └── src/
├── docs/                 # 기획/설계 문서
├── start-smartfuel.bat   # 원클릭 서버 실행
└── start-smartfuel.ps1   # 실행 스크립트 본체
```

---

## ⚠️ 주의사항

- `.env` 파일은 **절대 Git에 커밋하지 마세요**. `.gitignore`에 이미 포함되어 있습니다.
- `VITE_` 접두사가 붙은 환경변수는 빌드 시 브라우저 번들에 포함되므로 **Secret 키를 넣지 마세요**.
- `db.sqlite3`도 `.gitignore`에 포함되어 있으므로, clone 후 반드시 `migrate` 명령을 실행해야 합니다.
