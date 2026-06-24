<script setup>
import { reactive, ref, watch } from "vue";
import { Lock, Save, ShieldAlert, ShieldCheck } from "@lucide/vue";
import { loginAccount, updateCurrentUser } from "../api/accounts";

const props = defineProps({
  user: {
    type: Object,
    default: null
  }
});
const emit = defineEmits(["updated"]);

const form = reactive({
  username: "",
  email: ""
});
const confirmPassword = ref("");
const loading = ref(false);
const error = ref(null);
const authError = ref(null);
const saved = ref(false);
const authorized = ref(false);

watch(
  () => props.user,
  (user) => {
    form.username = user?.username || "";
    form.email = user?.email || "";
  },
  { immediate: true }
);

async function saveProfile() {
  loading.value = true;
  error.value = null;
  authError.value = null;
  saved.value = false;

  try {
    // 1. Authorization: Verify user's actual password before profile modifications
    try {
      await loginAccount({
        username: props.user.username,
        password: confirmPassword.value
      });
      authorized.value = true;
    } catch (err) {
      authorized.value = false;
      authError.value = "본인 확인에 실패했습니다. 비밀번호를 다시 확인해 주세요.";
      loading.value = false;
      return;
    }

    // 2. Perform actual PATCH update if authorized successfully
    await updateCurrentUser(form);
    saved.value = true;
    confirmPassword.value = ""; // clear password after success
    authorized.value = false;
    emit("updated");
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="singleColumn">
    <section class="panel">
      <div class="panelHeader">
        <div>
          <p class="eyebrow">My Page</p>
          <h2>마이페이지 및 회원정보 관리</h2>
        </div>
        <Lock :size="20" style="color: var(--slate-400);" />
      </div>

      <div style="background: var(--slate-50); border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px; font-size: 13px; color: var(--slate-600); line-height: 1.6;">
        🔒 <strong>정보 수정 시 보안 서약</strong><br />
        SmartFuel은 개인정보 보호를 위해 실제 회원 정보를 수정할 때 <strong>비밀번호 재인증(Authorization)</strong>을 필수로 요구합니다.
      </div>

      <form class="fieldGrid" @submit.prevent="saveProfile">
        <label>
          <span>사용자 계정 ID</span>
          <input v-model.trim="form.username" required placeholder="아이디 입력" />
        </label>

        <label>
          <span>이메일 주소</span>
          <input v-model.trim="form.email" type="email" placeholder="example@smartfuel.com" />
        </label>

        <!-- Secure Authorization Field -->
        <label style="border-top: 1px dashed var(--slate-200); padding-top: 16px; margin-top: 8px;">
          <span style="color: var(--primary); font-weight: 800; display: flex; align-items: center; gap: 4px;">
            🔑 현재 비밀번호 입력 (본인 인증 필수)
          </span>
          <input
            v-model="confirmPassword"
            type="password"
            required
            placeholder="본인 확인용 비밀번호를 입력해 주세요."
            style="border-color: var(--primary); background: var(--white);"
          />
        </label>

        <!-- Status strip inside form -->
        <div v-if="authError" class="errorPanel compact">
          <ShieldAlert :size="16" />
          <span>{{ authError }}</span>
        </div>

        <div v-if="error" class="errorPanel compact">
          <ShieldAlert :size="16" />
          <strong>{{ error.code || "PROFILE_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>

        <div v-if="saved" class="statusStrip" style="background: var(--primary-light); color: var(--primary); margin: 8px 0; border: 1px solid rgba(2, 132, 199, 0.2);">
          <ShieldCheck :size="16" />
          <span>성공적으로 회원 정보가 업데이트되었습니다.</span>
        </div>

        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <Save :size="18" />
          <span>{{ loading ? "인증 및 저장 중..." : "인증 후 정보 수정" }}</span>
        </button>
      </form>
    </section>
  </main>
</template>

