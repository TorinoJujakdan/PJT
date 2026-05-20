import { apiRequest } from "./client";

export function createRecommendationQuote(request) {
  return apiRequest("/recommendations/quote/", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

