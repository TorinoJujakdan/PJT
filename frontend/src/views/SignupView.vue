<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Check, UserPlus } from "@lucide/vue";
import { checkUsernameAvailability, signupAndAuthenticate } from "../api/accounts";

const emit = defineEmits(["authenticated", "go-login"]);

const form = reactive({
  username: "",
  email: "",
  password: "",
  passwordConfirm: "",
});

const usernameCheck = reactive({
  status: "idle",
  message: "",
  checkedUsername: "",
});

const loading = ref(false);
const error = ref(null);

const passwordRules = computed(() => [
  { key: "length", label: "8자 이상", passed: form.password.length >= 8 },
  { key: "letter", label: "영문 포함", passed: /[A-Za-z]/.test(form.password) },
  { key: "number", label: "숫자 포함", passed: /\d/.test(form.password) },
  { key: "special", label: "특수문자 포함", passed: /[^A-Za-z0-9]/.test(form.password) },
]);

const passwordIsValid = computed(() => passwordRules.value.every((rule) => rule.passed));
const passwordConfirmStatus = computed(() => {
  if (!form.passwordConfirm) return "idle";
  return form.password === form.passwordConfirm ? "valid" : "invalid";
});
const emailIsValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email));
const usernameIsAvailable = computed(
  () => usernameCheck.status === "available" && usernameCheck.checkedUsername === form.username
);
const canSubmit = computed(
  () =>
    Boolean(form.username.trim()) &&
    usernameIsAvailable.value &&
    emailIsValid.value &&
    passwordIsValid.value &&
    passwordConfirmStatus.value === "valid" &&
    !loading.value
);

watch(
  () => form.username,
  () => {
    usernameCheck.status = "idle";
    usernameCheck.message = "";
    usernameCheck.checkedUsername = "";
  }
);

async function checkUsername() {
  if (!form.username.trim() || usernameCheck.status === "checking") return;

  usernameCheck.status = "checking";
  usernameCheck.message = "";
  usernameCheck.checkedUsername = form.username;

  try {
    const payload = await checkUsernameAvailability(form.username);
    usernameCheck.status = payload.available ? "available" : "unavailable";
    usernameCheck.message = payload.message;
  } catch (err) {
    usernameCheck.status = "unavailable";
    usernameCheck.message = err.payload?.message || err.message;
  }
}

async function submit() {
  if (!canSubmit.value) return;

  loading.value = true;
  error.value = null;
  try {
    const payload = await signupAndAuthenticate({
      username: form.username,
      email: form.email,
      password: form.password,
    });
    emit("authenticated", payload.user);
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="singleColumn signupStandaloneShell">
    <section class="signupPageCard modernSignupCard">
      <div>
        <p class="eyebrow">START SMARTFUEL</p>
        <h2>회원가입</h2>
      </div>

      <form class="fieldGrid" @submit.prevent="submit">
        <div class="signupFieldCard">
          <div class="signupField">
            <label for="signup-username">
              <span>아이디</span>
            </label>
            <div class="duplicateCheckRow">
              <input
                id="signup-username"
                v-model.trim="form.username"
                autocomplete="username"
                required
                placeholder="사용할 아이디"
                aria-describedby="signup-username-status"
              />
              <button
                class="duplicateCheckButton"
                type="button"
                :disabled="!form.username.trim() || usernameCheck.status === 'checking'"
                @click="checkUsername"
              >
                {{ usernameCheck.status === "checking" ? "확인 중" : "중복확인" }}
              </button>
            </div>
          </div>
          <p
            v-if="usernameCheck.message || (form.username && !usernameIsAvailable)"
            id="signup-username-status"
            class="signupStatusText"
            :class="{
              success: usernameCheck.status === 'available',
              danger: usernameCheck.status === 'unavailable',
              muted: usernameCheck.status === 'idle' || usernameCheck.status === 'checking'
            }"
            role="status"
          >
            {{ usernameCheck.message || "아이디 중복확인을 완료해 주세요." }}
          </p>

          <label>
            <span>이메일</span>
            <input v-model.trim="form.email" type="email" autocomplete="email" required placeholder="you@example.com" />
          </label>

          <label>
            <span>비밀번호</span>
            <input v-model="form.password" type="password" autocomplete="new-password" required placeholder="비밀번호 입력" />
          </label>

          <ul class="passwordRuleList" aria-label="비밀번호 조건">
            <li v-for="rule in passwordRules" :key="rule.key" :class="{ passed: rule.passed }">
              <span><Check :size="13" /></span>
              {{ rule.label }}
            </li>
          </ul>

          <label>
            <span>비밀번호 확인</span>
            <input
              v-model="form.passwordConfirm"
              type="password"
              autocomplete="new-password"
              required
              placeholder="비밀번호를 다시 입력"
            />
          </label>
          <p
            v-if="passwordConfirmStatus !== 'idle'"
            class="signupStatusText"
            :class="{ success: passwordConfirmStatus === 'valid', danger: passwordConfirmStatus === 'invalid' }"
            role="status"
          >
            {{ passwordConfirmStatus === "valid" ? "비밀번호가 일치합니다." : "비밀번호가 일치하지 않습니다." }}
          </p>
        </div>

        <div v-if="error" class="errorPanel compact" role="alert">
          <strong>{{ error.code || "SIGNUP_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>

        <button class="primaryButton fullWidth" type="submit" :disabled="!canSubmit">
          <UserPlus :size="18" />
          <span>{{ loading ? "가입 처리 중..." : "계정 만들고 시작하기" }}</span>
        </button>
      </form>
    </section>
  </main>
</template>
