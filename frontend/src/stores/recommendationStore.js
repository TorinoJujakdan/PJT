import { reactive } from "vue";
import { createRecommendationQuote } from "../api/recommendations";

export const recommendationStore = reactive({
  loading: false,
  error: null,
  response: null,
  async quote(request) {
    this.loading = true;
    this.error = null;
    try {
      this.response = await createRecommendationQuote(request);
    } catch (error) {
      this.error = error.payload || {
        code: "REQUEST_FAILED",
        message: error.message
      };
    } finally {
      this.loading = false;
    }
  }
});

