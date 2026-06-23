<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Edit3, MessageSquare, Plus, Search, Trash2 } from "@lucide/vue";

import {
  createCommunityPost,
  deleteCommunityPost,
  listCommunityPosts,
  updateCommunityPost,
} from "../api/community";
import {
  canEditPost,
  formatCommunityError,
  parseTagInput,
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
const error = ref("");
const statusMessage = ref("");
const editingPostId = ref(null);

const filters = reactive({
  query: "",
  station_id: "",
  tag: "",
});

const form = reactive({
  station_id: "",
  title: "",
  content: "",
  tags: "",
});

const isEditing = computed(() => editingPostId.value !== null);
const canSubmit = computed(() => (
  props.isAuthenticated
  && String(form.station_id).trim()
  && form.title.trim()
  && form.content.trim()
  && !saving.value
));

function resetForm() {
  editingPostId.value = null;
  form.station_id = "";
  form.title = "";
  form.content = "";
  form.tags = "";
}

function fillFormForEdit(post) {
  editingPostId.value = post.id;
  form.station_id = post.station?.station_id ? String(post.station.station_id) : "";
  form.title = post.title || "";
  form.content = post.content || "";
  form.tags = tagsToInput(post.tags);
}

function requestLogin() {
  emit("login");
}

function buildFilters() {
  return {
    query: filters.query.trim(),
    station_id: filters.station_id.trim(),
    tag: filters.tag.trim(),
    limit: 50,
  };
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

async function submitPost() {
  if (!props.isAuthenticated) {
    requestLogin();
    return;
  }
  saving.value = true;
  error.value = "";
  statusMessage.value = "";
  const payload = {
    station_id: Number(form.station_id),
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

onMounted(loadPosts);
</script>

<template>
  <div class="communityWorkspace">
    <aside class="communityPanel">
      <div class="cardsSectionHeading communityHeading">
        <div>
          <p class="eyebrow">READ PUBLICLY</p>
          <h3>커뮤니티 검색</h3>
          <p>모든 사용자가 주유소 경험 게시글을 볼 수 있습니다.</p>
        </div>
      </div>

      <form class="communitySearchForm" @submit.prevent="loadPosts">
        <label>
          검색어
          <input v-model="filters.query" data-community-initial-focus type="search" placeholder="제목, 내용, 주유소명 검색" />
        </label>
        <label>
          주유소 ID
          <input v-model="filters.station_id" inputmode="numeric" placeholder="예: 1" />
        </label>
        <label>
          태그
          <input v-model="filters.tag" placeholder="예: clean" />
        </label>
        <button class="cardPrimaryButton" type="submit" :disabled="loading">
          <Search :size="16" />
          검색/필터 적용
        </button>
      </form>

      <div class="communityWriteGate">
        <template v-if="isAuthenticated">
          <p class="eyebrow">WRITE AS {{ user?.username }}</p>
          <h3>{{ isEditing ? "게시글 수정" : "게시글 작성" }}</h3>
          <p>실방문 인증 없이 경험을 공유합니다. 추천 순위에는 반영되지 않습니다.</p>
        </template>
        <template v-else>
          <p class="eyebrow">LOGIN REQUIRED</p>
          <h3>작성은 로그인 후 가능</h3>
          <p>목록 조회는 공개이며, 게시글 작성/수정/삭제만 로그인이 필요합니다.</p>
          <button class="cardPrimaryButton" type="button" @click="requestLogin">로그인하고 작성하기</button>
        </template>
      </div>

      <form v-if="isAuthenticated" class="communityPostForm" @submit.prevent="submitPost">
        <label>
          주유소 ID
          <input v-model="form.station_id" required inputmode="numeric" placeholder="게시글을 연결할 주유소 ID" />
        </label>
        <label>
          제목
          <input v-model="form.title" required maxlength="120" placeholder="예: 셀프 주유가 편했어요" />
        </label>
        <label>
          내용
          <textarea v-model="form.content" required maxlength="2000" rows="6" placeholder="주유소 이용 경험을 적어 주세요." />
        </label>
        <label>
          태그
          <input v-model="form.tags" placeholder="쉼표로 구분: clean, coffee" />
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

    <section class="communityPanel communityListPanel">
      <header class="communityListHeader">
        <div>
          <p class="eyebrow">POSTS</p>
          <h3>게시글 {{ meta.count }}개</h3>
          <p>기본 50개까지 조회하며 서버에서 최대 100개로 제한합니다.</p>
        </div>
        <button class="cardSecondaryButton" type="button" :disabled="loading" @click="loadPosts">새로고침</button>
      </header>

      <p v-if="error" class="cardError">{{ error }}</p>
      <p v-if="statusMessage" class="cardStatus">{{ statusMessage }}</p>

      <div v-if="loading" class="cardsEmptyState">
        <MessageSquare :size="28" />
        <strong>커뮤니티 게시글을 불러오는 중입니다.</strong>
      </div>

      <div v-else-if="!posts.length" class="cardsEmptyState">
        <MessageSquare :size="28" />
        <strong>아직 게시글이 없습니다.</strong>
        <span>첫 주유소 경험을 공유해 보세요.</span>
      </div>

      <article v-for="post in posts" v-else :key="post.id" class="communityPostCard">
        <div class="communityPostTop">
          <div>
            <p class="eyebrow">{{ post.station?.brand || "STATION" }}</p>
            <h4>{{ post.title }}</h4>
            <p>{{ post.station?.name }} · {{ post.station?.address }}</p>
          </div>
          <div v-if="canEditPost(post, user)" class="communityActions">
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
          </div>
        </div>

        <p class="communityPostContent">{{ post.content }}</p>
        <footer class="communityPostFooter">
          <span>작성자 {{ post.author?.username || "unknown" }}</span>
          <span>{{ new Date(post.created_at).toLocaleString() }}</span>
          <span v-for="tag in post.tags" :key="tag" class="communityTag">#{{ tag }}</span>
        </footer>
      </article>
    </section>
  </div>
</template>
