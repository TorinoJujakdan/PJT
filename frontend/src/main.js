import { createApp } from "vue";
import App from "./App.vue";
import "./styles.css";
import "./styles/unified-shell.css";
import "./styles/dashboard.css";
import "./styles/onboarding.css";

const app = createApp(App);

// 전역 에러 핸들러 (처리되지 않은 예외 감지)
app.config.errorHandler = (err, instance, info) => {
  if (import.meta.env.DEV) {
    console.error("[SmartFuel Error]", err, info);
  }
};

app.mount("#app");
