# SmartFuel 실무 레벨 아키텍처 개선 가이드라인

본 문서는 **SmartFuel** 프로젝트를 프로토타입 단계에서 실제 실무/운영 서비스 수준(Production-Ready)으로 고도화하기 위한 아키텍처 개선안 및 구현 가이드를 담고 있습니다.

---

## 1. Custom User Model 도입 (accounts 앱)

Django의 기본 User 모델을 그대로 사용하는 것은 실무에서 강한 안티패턴으로 여겨집니다. 비즈니스 요구사항 변화(휴대폰 번호 로그인, SNS 연동, 추가 프로필 데이터 등)에 대처하기 위해 프로젝트 초기 설계 단계에서 Custom User Model을 적용하는 것이 필수적입니다.

### 📌 개선 방향
- `accounts` 앱 내에 `AbstractUser`를 상속받는 커스텀 `User` 모델을 새로 선언합니다.
- `settings.py`에 `AUTH_USER_MODEL`을 등록합니다.

### 💻 코드 변경 예시

#### 1) `PJT/backend/accounts/models.py` 생성
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    실무 요구사항에 따라 기본 Django User에 추가 필드를 쉽게 선언할 수 있도록 
    AbstractUser를 상속받은 커스텀 User 모델입니다.
    """
    # 추가 필드가 현재 없더라도 상속 구조를 만들어 놓는 것이 중요합니다.
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="전화번호")
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name="닉네임")

    def __str__(self):
        return self.username
```

#### 2) `PJT/backend/core/settings.py` 수정
```python
# Custom User Model 등록
AUTH_USER_MODEL = "accounts.User"
```

> [!WARNING]
> **DB 마이그레이션 주의 사항**
> 이미 마이그레이션이 진행된 데이터베이스 환경에서 `AUTH_USER_MODEL`을 변경하면 foreign key 참조 오류가 발생하여 마이그레이션이 실패할 수 있습니다. 
> 로컬 환경이라면 기존 `db.sqlite3` 및 각 앱의 `migrations/000*_initial.py` 파일을 전부 제거하고 `makemigrations` 및 `migrate`를 완전히 처음부터 재수행하는 것을 권장합니다.

---

## 2. CORS Headers 및 배포 설정 (backend)

현재는 Vite 개발 서버의 로컬 프록시 설정에 전적으로 의존하고 있습니다. 실제 배포 환경에서 프론트엔드와 백엔드가 다른 서버/도메인으로 운영될 경우를 위해 Django 단에서 CORS 요청을 올바르게 처리해야 합니다.

### 📌 개선 방향
- `django-cors-headers` 라이브러리를 의존성에 추가합니다.
- 특정 호스트(예: 프론트엔드가 호스팅되는 도메인)에 대해서만 자원 공유를 수락하도록 화이트리스트를 구축합니다.

### 💻 코드 변경 예시

#### 1) `PJT/backend/requirements.txt` 추가
```text
django-cors-headers>=4.3.0
```

#### 2) `PJT/backend/core/settings.py` 반영
```python
INSTALLED_APPS = [
    ...
    "corsheaders",  # 추가
    "rest_framework",
    "accounts",
    ...
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # 공통 미들웨어보다 최상단에 배치해야 합니다.
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    ...
]

# CORS 설정 추가 (환경 변수 혹은 배포 환경에 따라 도메인을 관리합니다)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://smartfuel.yourdomain.com",  # 운영 프론트엔드 도메인 예시
]

# 쿠키 기반 인증을 공유할 수 있도록 설정
CORS_ALLOW_CREDENTIALS = True
```

---

## 3. JWT (JSON Web Token) 인증 도입

세션 쿠키 기반의 인증 체계에서 무상태(Stateless)하고 여러 도메인(모바일 앱 포함)에서 유연하게 활용 가능한 JWT 인증 체계로의 전환 가이드라인입니다.

### 📌 개선 방향
- `djangorestframework-simplejwt` 라이브러리를 사용하여 Token 발급 및 갱신 API를 구축합니다.
- 프론트엔드 Axios/Fetch 클라이언트에 인터셉터를 구현하여 토큰 만료 시 Refresh Token을 통한 재발급 로직을 자동화합니다.

### 💻 코드 변경 예시

#### 1) `PJT/backend/requirements.txt` 추가
```text
djangorestframework-simplejwt>=5.3.0
```

#### 2) `PJT/backend/core/settings.py` 인증 클래스 설정 변경
```python
from datetime import timedelta

# Simple JWT 디폴트 설정 정의
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",  # JWT 인증 주입
    ],
    ...
}
```

#### 3) `PJT/backend/core/urls.py` 라우팅 추가
```python
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    ...
    # JWT 토큰 발급 및 갱신 엔드포인트
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ...
]
```

---

## 4. Vue Router 및 Pinia 상태 관리 도입 (frontend)

현재는 App.vue 내부의 로컬 뷰 변경 상태 변수와 모달 제어로 모든 화면 전환을 처리하고 있어 코드가 매우 복잡해진 상태입니다. 모듈식 SPA 설계를 위한 기본 라우터 및 글로벌 상태 저장소 구축 방법입니다.

### 📌 개선 방향
- `vue-router`를 활용해 선언적 라우팅을 구축합니다.
- 사용자 인증 정보(User 객체, Access Token 등)를 `pinia` 글로벌 스토어에 보관하여 컴포넌트 간의 결합도를 낮춥니다.

### 💻 파일 구조 변경 및 코드 예시

#### 1) `package.json` 의존성 추가 설치
```json
"dependencies": {
  ...
  "vue-router": "^4.3.0",
  "pinia": "^2.1.0"
}
```

#### 2) `PJT/frontend/src/router/index.js` 라우팅 정의
```javascript
import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import { useAuthStore } from "../stores/authStore";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
  },
  {
    path: "/vehicles",
    name: "vehicles",
    component: () => import("../views/VehicleView.vue"),
    meta: { requiresAuth: true } // 인증이 필요한 라우트 플래그 설정
  },
  {
    path: "/cards",
    name: "cards",
    component: () => import("../views/CardsView.vue"),
    meta: { requiresAuth: true }
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 네비게이션 가드를 통한 비로그인 차단 기능 구현
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "home", query: { auth: "login" } });
  } else {
    next();
  }
});
```

#### 3) `PJT/frontend/src/stores/authStore.js` 사용자 글로벌 상태 관리
```javascript
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getCurrentUser, loginAccount, logoutAccount } from "../api/accounts";

export const useAuthStore = defineStore("auth", () => {
  const user = ref(null);
  const token = ref(localStorage.getItem("access_token") || null);

  const isAuthenticated = computed(() => !!user.value);

  async function checkAuth() {
    try {
      const data = await getCurrentUser();
      user.value = data.user;
    } catch {
      user.value = null;
      token.value = null;
      localStorage.removeItem("access_token");
    }
  }

  async function login(payload) {
    // API 서버에서 JWT 혹은 세션 갱신 처리
    const data = await loginAccount(payload);
    user.value = data.user;
    if (data.access_token) {
      token.value = data.access_token;
      localStorage.setItem("access_token", data.access_token);
    }
  }

  async function logout() {
    await logoutAccount();
    user.value = null;
    token.value = null;
    localStorage.removeItem("access_token");
  }

  return {
    user,
    token,
    isAuthenticated,
    checkAuth,
    login,
    logout,
  };
});
```

#### 4) `PJT/frontend/src/main.js` 미들웨어 바인딩
```javascript
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router";
import "./styles.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
```
