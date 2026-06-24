import { apiRequest } from "./client";


function buildQueryString(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}


export function listCommunityPosts(filters = {}) {
  return apiRequest(`/community/posts/${buildQueryString(filters)}`);
}


export function createCommunityPost(payload) {
  return apiRequest("/community/posts/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function updateCommunityPost(postId, payload) {
  return apiRequest(`/community/posts/${postId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}


export function deleteCommunityPost(postId) {
  return apiRequest(`/community/posts/${postId}/`, {
    method: "DELETE",
  });
}


export function starCommunityPost(postId) {
  return apiRequest(`/community/posts/${postId}/star/`, {
    method: "POST",
  });
}


export function unstarCommunityPost(postId) {
  return apiRequest(`/community/posts/${postId}/star/`, {
    method: "DELETE",
  });
}
