import { ref } from "vue";

export function useModalState() {
  const activeModal = ref(null);
  const modalReturnFocus = ref(null);
  const authModalMode = ref("login");

  function openModal(modalType, extra = null) {
    if (modalType === "auth") {
      authModalMode.value = extra || "login";
    }
    modalReturnFocus.value = document.activeElement;
    activeModal.value = modalType;
  }

  function hideModal() {
    activeModal.value = null;
  }

  function closeModal() {
    hideModal();
    requestAnimationFrame(() => modalReturnFocus.value?.focus?.());
  }

  return {
    activeModal,
    authModalMode,
    openModal,
    closeModal,
    hideModal,
  };
}
