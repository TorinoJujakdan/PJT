import { computed, reactive } from "vue";
import { getCurrentUser, logoutAccount } from "../api/accounts";
import { resetCardsWorkspace } from "../stores/cardsWorkspaceStore";

export function useAuthSession({
  afterLogin,
  clearUserResources,
  resetAfterLogout,
  hideModal,
} = {}) {
  const auth = reactive({
    loading: true,
    user: null,
    error: null,
  });

  const isAuthenticated = computed(() => Boolean(auth.user));

  async function refreshMe() {
    auth.loading = true;
    auth.error = null;
    try {
      const payload = await getCurrentUser();
      auth.user = payload.authenticated ? payload.user : null;
      if (auth.user) {
        await afterLogin?.();
      } else {
        clearUserResources?.();
      }
    } catch (error) {
      auth.error = error.payload || { message: error.message };
    } finally {
      auth.loading = false;
    }
  }

  async function handleAuthenticated(user) {
    auth.user = user;
    hideModal?.();
    await afterLogin?.();
  }

  async function handleLogout() {
    await logoutAccount();
    hideModal?.();
    resetCardsWorkspace();
    auth.user = null;
    clearUserResources?.();
    resetAfterLogout?.();
  }

  return {
    auth,
    isAuthenticated,
    refreshMe,
    handleAuthenticated,
    handleLogout,
  };
}
