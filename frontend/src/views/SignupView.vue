<script setup>
import { reactive, ref } from "vue";
import { UserPlus } from "@lucide/vue";
import { signupAccount } from "../api/accounts";

const emit = defineEmits(["authenticated", "go-login"]);

const form = reactive({
  username: "",
  email: "",
  password: ""
});
const loading = ref(false);
const error = ref(null);

async function submit() {
  loading.value = true;
  error.value = null;
  try {
    const payload = await signupAccount(form);
    emit("authenticated", payload.user);
  } catch (err) {
    error.value = err.payload || { message: err.message };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="singleColumn">
    <section class="panel formPanel">
      <div class="panelHeader">
        <div>
          <p class="eyebrow">Signup</p>
          <h2>회원가입</h2>
        </div>
      </div>
      <form class="fieldGrid" @submit.prevent="submit">
        <label>
          <span>아이디</span>
          <input v-model.trim="form.username" autocomplete="username" required />
        </label>
        <label>
          <span>이메일</span>
          <input v-model.trim="form.email" type="email" autocomplete="email" required />
        </label>
        <label>
          <span>비밀번호</span>
          <input v-model="form.password" type="password" autocomplete="new-password" required />
        </label>
        <div v-if="error" class="errorPanel compact">
          <strong>{{ error.code || "SIGNUP_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <UserPlus :size="18" />
          <span>{{ loading ? "가입 중" : "가입하기" }}</span>
        </button>
        <button class="textButton" type="button" @click="emit('go-login')">로그인으로 이동</button>
      </form>
    </section>
  </main>
</template>
