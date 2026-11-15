<script setup>
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'
import { useStatusStore } from '@/stores/status'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'

const { t } = useI18n()
const auth_store = useAuthStore()
const status_store = useStatusStore()
const toast = use_toast()
const { run } = use_async_action()
const { status } = storeToRefs(status_store)

const dialog_open = ref(false)
const updating = ref(false)

// 本次会话内用户关闭弹窗后不再重复弹出（状态推送会持续携带 has_update）
let dismissed_in_session = false

watch(
  () => status.value?.has_update,
  (has_update) => {
    if (has_update && !dismissed_in_session) dialog_open.value = true
  },
  { immediate: true },
)

function toggle_dialog(open) {
  dialog_open.value = open
  if (!open) dismissed_in_session = true
}

function view_details() {
  toggle_dialog(false)
  window.open(
    'https://github.com/MineJPGcraft/UniBot/releases/latest',
    '_blank',
    'noopener,noreferrer',
  )
}

async function update_bot() {
  const ok = await run(() => status_store.update_bot(), t('layout.update_failed'), updating)
  if (!ok) return
  toggle_dialog(false)
  toast.success(t('layout.update_success_toast'))
}
</script>

<template>
  <Dialog
    :model-value="dialog_open"
    :title="t('layout.update_dialog_title')"
    :description="
      t('layout.update_version_info', {
        current: status?.version || '—',
        latest: status?.latest_version || '—',
      })
    "
    hide-footer
    width="min(420px, calc(100vw - 32px))"
    @update:model-value="toggle_dialog"
  >
    <p class="update-hint">
      <Icon icon="lucide:arrow-up-circle" width="15" />
      {{ t('layout.update_hint') }}
    </p>
    <div class="update-actions">
      <Button variant="ghost" @click="toggle_dialog(false)">
        {{ t('layout.update_later') }}
      </Button>
      <Button variant="secondary" @click="view_details">
        {{ t('layout.update_view_details') }}
      </Button>
      <Button v-if="auth_store.is_admin" variant="primary" :loading="updating" @click="update_bot">
        <Icon icon="lucide:download" width="15" />
        {{ t('layout.update_now') }}
      </Button>
    </div>
  </Dialog>
</template>

<style scoped>
.update-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--warning-soft);
  color: var(--warning);
  font-size: var(--text-sm);
}

.update-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
