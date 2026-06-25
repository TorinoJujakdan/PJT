<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Edit3, MessageSquare, Plus, Search, Star, Trash2 } from "@lucide/vue";

import {
  createCommunityPost,
  deleteCommunityPost,
  listCommunityPosts,
  starCommunityPost,
  unstarCommunityPost,
  updateCommunityPost,
} from "../api/community";
import {
  canEditPost,
  formatCommunityError,
  getStarredButtonLabel,
  parseTagInput,
  removePostById,
  replacePostById,
  tagsToInput,
} from "../components/community/communityPresentation";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["login"]);

const posts = ref([]);
const meta = ref({ count: 0, limit: 50 });
const loading = ref(false);
const saving = ref(false);
const deletingId = ref(null);
const starringId = ref(null);
const error = ref("");
const statusMessage = ref("");
const editingPostId = ref(null);
const activePostScope = ref("all");

const filters = reactive({
  query: "",
  tag: "",
});

const form = reactive({
  title: "",
  content: "",
  tags: "",
});

const isEditing = computed(() => editingPostId.value !== null);
const isStarredScope = computed(() => activePostScope.value === "starred");
const canSubmit = computed(() => (
  props.isAuthenticated
  && form.title.trim()
  && form.content.trim()
  && !saving.value
));
const emptyTitle = computed(() => (
  isStarredScope.value ? "아직 스크랩한 게시글이 없습니다." : "아직 게시글이 없습니다."
));
const emptyDescription = computed(() => (
  isStarredScope.value
    ? "마음에 드는 게시글을 스크랩하여 나중에 다시 모아보세요."
    : "첫 게시글을 작성해 커뮤니티를 시작해 보세요."
));

function resetForm() {
  editingPostId.value = null;
  form.title = "";
  form.content = "";
  form.tags = "";
}

function fillFormForEdit(post) {
  editingPostId.value = post.id;
  form.title = post.title || "";
  form.content = post.content || "";
  form.tags = tagsToInput(post.tags);
}

function requestLogin() {
  emit("login");
}

function buildFilters() {
  const nextFilters = {
    query: filters.query.trim(),
    tag: filters.tag.trim(),
    limit: 50,
  };
  if (isStarredScope.value) nextFilters.starred = true;
  return nextFilters;
}

async function loadPosts() {
  loading.value = true;
  error.value = "";
  try {
    const payload = await listCommunityPosts(buildFilters());
    posts.value = payload.posts || [];
    meta.value = payload.meta || { count: posts.value.length, limit: 50 };
  } catch (requestError) {
    error.value = formatCommunityError(requestError);
  } finally {
    loading.value = false;
  }
}

async function setPostScope(scope) {
  if (scope === "starred" && !props.isAuthenticated) {
    requestLogin();
    return;
  }
  if (activePostScope.value === scope) return;
  activePostScope.value = scope;
  statusMessage.value = "";
  await loadPosts();
}

async function submitPost() {
  if (!props.isAuthenticated) {
    requestLogin();
    return;
  }
  saving.value = true;
  error.value = "";
  statusMessage.value = "";
  const payload = {
    title: form.title,
    content: form.content,
    tags: parseTagInput(form.tags),
  };

  try {
    if (isEditing.value) {
      await updateCommunityPost(editingPostId.value, payload);
      statusMessage.value = "게시글을 수정했습니다.";
    } else {
      await createCommunityPost(payload);
      activePostScope.value = "all";
      statusMessage.value = "게시글을 등록했습니다.";
    }
    resetForm();
    await loadPosts();
  } catch (requestError) {
    error.value = formatCommunityError(requestError);
  } finally {
    saving.value = false;
  }
}

async function toggleStar(post) {
  if (!props.isAuthenticated) {
    requestLogin();
    return;
  }

  const wasStarred = Boolean(post.is_starred);
  starringId.value = post.id;
  error.value = "";
  statusMessage.value = "";

  try {
    const updatedPost = wasStarred
      ? await unstarCommunityPost(post.id)
      : await starCommunityPost(post.id);

    if (isStarredScope.value && wasStarred) {
      posts.value = removePostById(posts.value, post.id);
      meta.value = { ...meta.value, count: posts.value.length };
    } else {
      posts.value = replacePostById(posts.value, updatedPost);
    }

    statusMessage.value = updatedPost.is_starred ? "스크랩했습니다." : "스크랩을 해제했습니다.";
  } catch (requestError) {
    error.value = formatCommunityError(requestError);
  } finally {
    starringId.value = null;
  }
}

async function removePost(post) {
  if (!canEditPost(post, props.user)) return;
  const ok = window.confirm("이 커뮤니티 게시글을 삭제할까요?");
  if (!ok) return;

  deletingId.value = post.id;
  error.value = "";
  statusMessage.value = "";
  try {
    await deleteCommunityPost(post.id);
    statusMessage.value = "게시글을 삭제했습니다.";
    if (editingPostId.value === post.id) resetForm();
    await loadPosts();
  } catch (requestError) {
    error.value = formatCommunityError(requestError);
  } finally {
    deletingId.value = null;
  }
}

watch(
  () => props.isAuthenticated,
  async (isAuthenticated) => {
    if (!isAuthenticated && isStarredScope.value) activePostScope.value = "all";
    await loadPosts();
  },
);

onMounted(loadPosts);
</script>

<template>
  <div class="communityWorkspace">
    <aside class="communityPanel communityWritePanel" aria-labelledby="community-write-title">
      <div class="cardsSectionHeading communityHeading">
        <div>
          <h3 id="community-write-title">{{ isEditing ? "게시글 수정" : "게시글 작성" }}</h3>
          <p>제목, 내용, 태그만으로 커뮤니티 글을 남길 수 있습니다.</p>
        </div>
      </div>

      <div v-if="!isAuthenticated" class="communityWriteGate">
        <p class="eyebrow">LOGIN REQUIRED</p>
        <h3>작성과 스크랩 저장은 로그인이 필요합니다</h3>
        <p>목록 조회와 검색은 공개이며, 게시글 작성·수정·삭제와 스크랩 저장만 로그인이 필요합니다.</p>
        <button class="cardPrimaryButton" type="button" @click="requestLogin">로그인하고 작성하기</button>
      </div>

      <form v-if="isAuthenticated" class="communityPostForm" @submit.prevent="submitPost">
        <label>
          제목
          <input
            v-model="form.title"
            data-community-initial-focus
            required
            maxlength="120"
            placeholder="예: 오늘 발견한 절약 팁"
          />
        </label>
        <label>
          내용
          <textarea
            v-model="form.content"
            required
            maxlength="2000"
            rows="9"
            placeholder="공유하고 싶은 경험이나 정보를 적어 주세요."
          />
        </label>
        <label>
          태그
          <input v-model="form.tags" placeholder="쉼표로 구분: 절약, 정보, 질문" />
        </label>
        <div class="communityFormActions">
          <button class="cardPrimaryButton" type="submit" :disabled="!canSubmit">
            <Plus v-if="!isEditing" :size="16" />
            <Edit3 v-else :size="16" />
            {{ saving ? "저장 중..." : isEditing ? "수정 저장" : "게시글 등록" }}
          </button>
          <button v-if="isEditing" class="cardSecondaryButton" type="button" @click="resetForm">취소</button>
        </div>
      </form>
    </aside>

    <section class="communityPanel communityListPanel" aria-labelledby="community-list-title">
      <header class="communityListHeader">
        <div>
          <p class="eyebrow">POSTS</p>
          <h3 id="community-list-title">{{ isStarredScope ? "스크랩한 게시글" : "게시글" }} {{ meta.count }}개</h3>
          <p>최근 게시글을 최대 {{ meta.limit }}개까지 보여줍니다.</p>
        </div>
        <button class="cardSecondaryButton" type="button" :disabled="loading" @click="loadPosts">새로고침</button>
      </header>

      <div class="communityViewTabs" role="tablist" aria-label="커뮤니티 게시글 보기">
        <button
          type="button"
          role="tab"
          :aria-selected="activePostScope === 'all'"
          :class="{ active: activePostScope === 'all' }"
          @click="setPostScope('all')"
        >
          전체 글
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="activePostScope === 'starred'"
          :class="{ active: activePostScope === 'starred' }"
          @click="setPostScope('starred')"
        >
          <Star :size="15" />
          스크랩
        </button>
      </div>

      <form class="communitySearchForm communityListSearch" role="search" @submit.prevent="loadPosts">
        <label>
          검색어
          <input v-model="filters.query" type="search" placeholder="제목, 내용, 태그 검색" />
        </label>
        <label>
          태그
          <input v-model="filters.tag" placeholder="예: 절약" />
        </label>
        <button class="cardPrimaryButton" type="submit" :disabled="loading">
          <Search :size="16" />
          게시글 검색
        </button>
      </form>

      <p v-if="error" class="cardError">{{ error }}</p>
      <p v-if="statusMessage" class="cardStatus">{{ statusMessage }}</p>

      <div v-if="loading" class="cardsEmptyState">
        <MessageSquare :size="28" />
        <strong>커뮤니티 게시글을 불러오는 중입니다.</strong>
      </div>

      <div v-else-if="!posts.length" class="cardsEmptyState">
        <MessageSquare :size="28" />
        <strong>{{ emptyTitle }}</strong>
        <span>{{ emptyDescription }}</span>
      </div>

      <article v-for="post in posts" v-else :key="post.id" class="communityPostCard">
        <div class="communityPostTop">
          <div>
            <p class="eyebrow">COMMUNITY</p>
            <h4>{{ post.title }}</h4>
            <p>작성자 {{ post.author?.username || "unknown" }}</p>
          </div>
          <div class="communityActions">
            <button
              class="cardIconButton star"
              type="button"
              :class="{ active: post.is_starred }"
              :aria-label="getStarredButtonLabel(post)"
              :aria-pressed="Boolean(post.is_starred)"
              :disabled="starringId === post.id"
              @click="toggleStar(post)"
            >
              <Star :size="16" :fill="post.is_starred ? 'currentColor' : 'none'" />
            </button>
            <template v-if="canEditPost(post, user)">
              <button class="cardIconButton" type="button" aria-label="게시글 수정" @click="fillFormForEdit(post)">
                <Edit3 :size="16" />
              </button>
              <button
                class="cardIconButton danger"
                type="button"
                aria-label="게시글 삭제"
                :disabled="deletingId === post.id"
                @click="removePost(post)"
              >
                <Trash2 :size="16" />
              </button>
            </template>
          </div>
        </div>

        <p class="communityPostContent">{{ post.content }}</p>
        <footer class="communityPostFooter">
          <span>{{ new Date(post.created_at).toLocaleString() }}</span>
          <span v-for="tag in post.tags" :key="tag" class="communityTag">#{{ tag }}</span>
        </footer>
      </article>
    </section>
  </div>
</template>
