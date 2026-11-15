<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useAdapterStore } from '@/stores/adapter'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import { use_restart } from '@/composables/use_restart'
import { use_task_submit } from '@/composables/use_task_submit'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Switch from '@/components/ui/Switch.vue'

const adapter_store = useAdapterStore()
const auth_store = useAuthStore()
const { t } = useI18n()
const toast = use_toast()
const { run } = use_async_action()
const { ask_restart } = use_restart()
const { submit_task, maybe_ask_restart } = use_task_submit()
const router = useRouter()
const { registered_list, catalog, loading } = storeToRefs(adapter_store)

const installing_adapter = ref('')
const toggling_adapter = ref('')
const uninstalling_adapter = ref('')
const uninstall_dialog_open = ref(false)
const pending_uninstall = ref(null)

const adapter_items = computed(() => {
  const catalog_modules = new Set(catalog.value.map((adapter) => adapter.module_name))
  const custom_adapters = registered_list.value
    .filter((adapter) => !catalog_modules.has(adapter.module_name))
    .map((adapter) => ({
      id: adapter.module_name,
      name: adapter.name,
      module_name: adapter.module_name,
      description: t('adapters.custom_description'),
      platforms: [],
      registered: true,
      removable: adapter.removable !== false,
    }))
  // 透传 config_keys 字段供「配置」按钮使用
  const catalog_items = catalog.value.map((adapter) => ({
    ...adapter,
    config_keys: adapter.config_keys || [],
  }))
  return [...catalog_items, ...custom_adapters]
})

onMounted(async () => {
  await run(() => adapter_store.fetch_all(), t('adapters.fetch_failed'))
})

async function install_adapter(adapter) {
  installing_adapter.value = adapter.id
  const task = await submit_task(
    () => adapter_store.install(adapter.id),
    t('adapters.install_failed'),
  )
  installing_adapter.value = ''
  if (task) {
    toast.success(t('adapters.install_success', { name: adapter.name }))
    // 依赖安装完成后才询问是否重启（task.result.restart_required 由后端标记）
    maybe_ask_restart(task, t('adapters.restart_after_install_confirm', { name: adapter.name }))
  }
}

async function toggle_adapter(adapter, enabled) {
  toggling_adapter.value = adapter.id
  const ok = await run(
    () => adapter_store.toggle_register(adapter.name, adapter.module_name, enabled),
    t('adapters.toggle_failed'),
  )
  toggling_adapter.value = ''
  if (ok) {
    toast.success(
      enabled
        ? t('adapters.enable_success', { name: adapter.name })
        : t('adapters.disable_success', { name: adapter.name }),
    )
    ask_restart(t('adapters.restart_after_toggle_confirm', { name: adapter.name }))
  }
}

function confirm_uninstall(adapter) {
  pending_uninstall.value = adapter
  uninstall_dialog_open.value = true
}

/**
 * 跳转到该适配器对应的环境变量配置项组。
 * 通过第一个 config_key 在 env_groups 中定位所属 group。
 */
function goto_adapter_config(adapter) {
  const keys = adapter.config_keys || []
  if (keys.length === 0) {
    toast.info(t('adapters.no_config_hint', { name: adapter.name }))
    return
  }
  router.push({ name: 'ConfigView', query: { tab: 'env', key: keys[0] } })
}

async function do_uninstall() {
  const adapter = pending_uninstall.value
  if (!adapter) return
  uninstalling_adapter.value = adapter.module_name
  const task = await submit_task(
    () => adapter_store.uninstall(adapter.name, adapter.module_name),
    t('adapters.uninstall_failed'),
  )
  uninstalling_adapter.value = ''
  if (task) {
    toast.success(t('adapters.uninstall_success', { name: adapter.name }))
    uninstall_dialog_open.value = false
    pending_uninstall.value = null
    maybe_ask_restart(task, t('adapters.restart_after_uninstall_confirm', { name: adapter.name }))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('adapters.page_title') }}</h1>
        <p class="page-desc">{{ t('adapters.page_description') }}</p>
      </div>
    </div>

    <section class="adapter-panel card">
      <div v-if="loading" class="loading-block">
        <Spinner :size="18" /> {{ t('common.loading') }}
      </div>
      <p v-else-if="adapter_items.length === 0" class="adapter-empty">
        {{ t('adapters.empty_list') }}
      </p>
      <ul v-else class="adapter-list">
        <li v-for="adapter in adapter_items" :key="adapter.id" class="adapter-row">
          <div class="adapter-icon"><Icon icon="lucide:unplug" width="18" /></div>
          <div class="adapter-main">
            <div class="adapter-title">
              <h3>{{ adapter.name }}</h3>
              <Badge
                :variant="
                  adapter.registered ? 'success' : adapter.installed ? 'warning' : 'neutral'
                "
              >
                {{
                  adapter.registered
                    ? t('common.enabled')
                    : adapter.installed
                      ? t('common.disabled')
                      : t('adapters.status_not_installed')
                }}
              </Badge>
            </div>
            <span class="adapter-package mono">{{ adapter.package || adapter.module_name }}</span>
            <p class="adapter-description">{{ adapter.description }}</p>
          </div>
          <div class="adapter-platforms">
            <span v-for="platform in adapter.platforms || []" :key="platform">{{ platform }}</span>
          </div>
          <div class="adapter-actions">
            <template v-if="adapter.removable === false">
              <span class="protected-adapter" :title="t('adapters.protected_tooltip')">
                <Icon icon="lucide:lock-keyhole" width="15" />
                {{ t('adapters.protected_label') }}
              </span>
              <Button
                v-if="adapter.config_keys && adapter.config_keys.length > 0"
                variant="ghost"
                size="sm"
                icon-only
                :title="t('adapters.config_button_title')"
                :disabled="!auth_store.is_admin"
                @click="goto_adapter_config(adapter)"
              >
                <Icon icon="lucide:settings" width="15" />
              </Button>
            </template>
            <template v-else-if="adapter.installed">
              <Switch
                :model-value="adapter.registered"
                :disabled="!auth_store.is_admin || toggling_adapter === adapter.id"
                @update:model-value="(val) => toggle_adapter(adapter, val)"
                :title="
                  adapter.registered
                    ? t('adapters.disable_toggle_tooltip')
                    : t('adapters.enable_toggle_tooltip')
                "
              />
              <div class="action-group">
                <Button
                  variant="ghost"
                  size="sm"
                  icon-only
                  :title="t('adapters.config_button_title')"
                  :disabled="!auth_store.is_admin"
                  @click="goto_adapter_config(adapter)"
                >
                  <Icon icon="lucide:settings" width="15" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  icon-only
                  :title="t('adapters.uninstall_button_title')"
                  :disabled="!auth_store.is_admin || Boolean(uninstalling_adapter)"
                  :loading="uninstalling_adapter === adapter.module_name"
                  @click="confirm_uninstall(adapter)"
                >
                  <Icon icon="lucide:trash-2" width="15" />
                </Button>
              </div>
            </template>
            <template v-else>
              <Button
                variant="secondary"
                size="sm"
                :disabled="!auth_store.is_admin || Boolean(installing_adapter)"
                :loading="installing_adapter === adapter.id"
                @click="install_adapter(adapter)"
              >
                <Icon icon="lucide:download" width="14" />
                {{ t('adapters.install_action') }}
              </Button>
            </template>
          </div>
        </li>
      </ul>
    </section>

    <Dialog
      v-model="uninstall_dialog_open"
      :title="t('adapters.uninstall_dialog_title')"
      :description="
        t('adapters.uninstall_dialog_description', { name: pending_uninstall?.name || '' })
      "
      :confirm-text="t('adapters.uninstall_dialog_confirm')"
      confirm-variant="danger"
      :loading="Boolean(uninstalling_adapter)"
      @confirm="do_uninstall"
    >
      <p class="uninstall-warning">
        <Icon icon="lucide:alert-triangle" width="16" />
        {{ t('adapters.uninstall_warning') }}
      </p>
    </Dialog>
  </div>
</template>

<style scoped>
.adapter-panel {
  margin-top: var(--space-4);
  overflow: hidden;
}

.adapter-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.adapter-list {
  padding: 0 var(--space-5);
}

.adapter-row {
  display: grid;
  grid-template-columns: 38px minmax(280px, 1fr) minmax(120px, auto) 140px;
  align-items: center;
  gap: var(--space-3);
  min-height: 92px;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border);
}

.adapter-row:last-child {
  border-bottom: none;
}

.adapter-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent);
}

.adapter-main {
  min-width: 0;
}

.adapter-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.adapter-title h3 {
  font-size: var(--text-sm);
  font-weight: 600;
}

.adapter-package {
  display: block;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.adapter-description {
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.adapter-platforms {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.adapter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.protected-adapter {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.action-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.uninstall-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: var(--text-sm);
}
</style>
