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


export function formatCommunityError(error, fallback = "\ucee4\ubba4\ub2c8\ud2f0 \uc694\uccad\uc744 \ucc98\ub9ac\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.") {
  const code = error?.payload?.code;
  if (code === "AUTHENTICATION_REQUIRED") return "\ub85c\uadf8\uc778 \ud6c4 \uc774\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.";
  if (code === "COMMUNITY_POST_FORBIDDEN") return "\uc791\uc131\uc790\ub9cc \uc218\uc815\ud558\uac70\ub098 \uc0ad\uc81c\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.";
  if (code === "INVALID_COMMUNITY_POST") return "\ubd80\uc801\uc808\ud55c \uba54\uc138\uc9c0 \uc785\ub2c8\ub2e4";
  return error?.payload?.message || error?.message || fallback;
}


export function canEditPost(post, user) {
  if (typeof post?.can_edit === "boolean") return post.can_edit;
  return Boolean(user?.id && post?.author?.id === user.id);
}


export function replacePostById(posts = [], updatedPost) {
  if (!updatedPost?.id) return posts;
  return posts.map((post) => (post.id === updatedPost.id ? { ...post, ...updatedPost } : post));
}


export function removePostById(posts = [], postId) {
  return posts.filter((post) => post.id !== postId);
}


export function getStarredButtonLabel(post) {
  return post?.is_starred ? "\ubcc4\ud45c \ud574\uc81c" : "\ubcc4\ud45c \uc800\uc7a5";
}
