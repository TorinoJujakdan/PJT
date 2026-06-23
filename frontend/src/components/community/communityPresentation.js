export function parseTagInput(value) {
  if (!value) return [];
  const seen = new Set();
  return String(value)
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag) => {
      const key = tag.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 10);
}


export function tagsToInput(tags = []) {
  return Array.isArray(tags) ? tags.join(", ") : "";
}


export function formatCommunityError(error, fallback = "커뮤니티 요청을 처리하지 못했습니다.") {
  const code = error?.payload?.code;
  if (code === "AUTHENTICATION_REQUIRED") return "로그인 후 이용할 수 있습니다.";
  if (code === "COMMUNITY_POST_FORBIDDEN") return "작성자만 수정하거나 삭제할 수 있습니다.";
  if (code === "STATION_NOT_FOUND") return "해당 주유소를 찾을 수 없습니다. 주유소 ID를 확인해 주세요.";
  if (code === "INVALID_COMMUNITY_POST") return "게시글 입력값을 확인해 주세요.";
  return error?.payload?.message || error?.message || fallback;
}


export function canEditPost(post, user) {
  if (typeof post?.can_edit === "boolean") return post.can_edit;
  return Boolean(user?.id && post?.author?.id === user.id);
}
