<script setup>
import { reactive, ref } from "vue";
import { LogIn } from "@lucide/vue";
import { loginAccount } from "../api/accounts";

const emit = defineEmits(["authenticated", "go-signup"]);

const form = reactive({
  username: "",
  password: ""
});
const loading = ref(false);
const error = ref(null);

async function submit() {
  loading.value = true;
  error.value = null;
  try {
    const payload = await loginAccount(form);
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
          <p class="eyebrow">Login</p>
          <h2>로그인</h2>
        </div>
      </div>
      <form class="fieldGrid" @submit.prevent="submit">
        <label>
          <span>아이디</span>
          <input v-model.trim="form.username" autocomplete="username" required />
        </label>
        <label>
          <span>비밀번호</span>
          <input v-model="form.password" type="password" autocomplete="current-password" required />
        </label>
        <div v-if="error" class="errorPanel compact">
          <strong>{{ error.code || "LOGIN_FAILED" }}</strong>
          <span>{{ error.message }}</span>
        </div>
        <button class="primaryButton fullWidth" type="submit" :disabled="loading">
          <LogIn :size="18" />
          <span>{{ loading ? "확인 중" : "로그인" }}</span>
        </button>
        <button class="textButton" type="button" @click="emit('go-signup')">계정 만들기</button>
      </form>
    </section>
  </main>
</template>
