<script setup>
import { reactive, ref } from "vue";
import { LogIn, UserPlus, X } from "@lucide/vue";
import { loginAccount, signupAndAuthenticate } from "../api/accounts";

const props = defineProps({
  initialMode: {
    type: String,
    default: "login" // 'login' or 'signup'
  }
});

const emit = defineEmits(["close", "authenticated"]);

const mode = ref(props.initialMode);
const loading = ref(false);
const error = ref(null);

const loginForm = reactive({
  username: "",
  password: ""
});

const signupForm = reactive({
  username: "",
  email: "",
  password: ""
});

async function handleLogin() {
  loading.value = true;
  error.value = null;
  try {
    const payload = await loginAccount(loginForm);
    emit("authenticated", payload.user);
    emit("close");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}

async function handleSignup() {
  loading.value = true;
  error.value = null;
  try {
    const payload = await signupAndAuthenticate(signupForm);
    emit("authenticated", payload.user);
    emit("close");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}

function switchMode(newMode) {
  mode.value = newMode;
  error.value = null;
}
</script>

<template>
  <div class="glassModalOverlay" @click.self="emit('close')">
    <div class="glassModalContainer" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <header class="glassModalHeader">
        <h2 id="auth-modal-title">{{ mode === 'login' ? '로그인' : '회원가입' }}</h2>
        <button class="glassModalCloseBtn" type="button" @click="emit('close')" aria-label="닫기">
          <X :size="16" />
        </button>
      </header>

      <!-- LOGIN MODE -->
      <form v-if="mode === 'login'" class="fieldGrid" @submit.prevent="handleLogin">
        <label>
          <span>아이디</span>
          <input v-model.trim="loginForm.username" autocomplete="username" required placeholder="아이디를 입력해 주세요." />
        </label>
        <label>
          <span>비밀번호</span>
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required placeholder="비밀번호를 입력해 주세요." />
        </label>
        <div v-if="error" class="errorPanel compact">
          <strong>{{ error.code || "LOGIN_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <LogIn :size="18" />
          <span>{{ loading ? "로그인 중..." : "로그인" }}</span>
        </button>
      </form>

      <!-- SIGNUP MODE -->
      <form v-else class="fieldGrid" @submit.prevent="handleSignup">
        <label>
          <span>아이디</span>
          <input v-model.trim="signupForm.username" autocomplete="username" required placeholder="원하는 아이디를 입력해 주세요." />
        </label>
        <label>
          <span>이메일</span>
          <input v-model.trim="signupForm.email" type="email" autocomplete="email" required placeholder="이메일 주소를 입력해 주세요." />
        </label>
        <label>
          <span>비밀번호</span>
          <input v-model="signupForm.password" type="password" autocomplete="new-password" required placeholder="비밀번호를 입력해 주세요." />
        </label>
        <div v-if="error" class="errorPanel compact">
          <strong>{{ error.code || "SIGNUP_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <UserPlus :size="18" />
          <span>{{ loading ? "가입 처리 중..." : "가입하기" }}</span>
        </button>
      </form>
    </div>
  </div>
</template>
