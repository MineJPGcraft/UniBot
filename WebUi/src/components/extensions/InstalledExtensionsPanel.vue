<script setup>
/**
 * 扩展管理：已安装扩展面板。
 *
 * 卡片网格展示已安装扩展：类型 / 状态徽标、描述与失败原因、配置 / 卸载 / 启停操作。
 * 扩展配置弹窗也由此面板持有（配置入口在卡片上），`ExtensionConfigDialog` 所需的
 * 详情与配置值从 extension store 读取。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useExtensionStore } from '@/stores/extension'
import { useAuthStore } from '@/stores/auth'
import { use_extension_labels } from '@/composables/use_extension_labels'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'
import { use_task_submit } from '@/composables/use_task_submit'
import { use_async_action } from '@/composables/use_async_action'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Switch from '@/components/ui/Switch.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ExtensionConfigDialog from '@/components/ExtensionConfigDialog.vue'

const emit = defineEmits(['changed'])

const { t } = useI18n()
const extension_store = useExtensionStore()
const auth_store = useAuthStore()
const toast = use_toast()
const { run } = use_async_action()
const { ask_restart } = use_restart()
const { submit_task } = use_task_submit()
const { type_badges, state_label, state_variant } = use_extension_labels()
const {
  installed_list,
  loading,
  detail,
  detail_loading,
  config_values,
  config_loading,
  saving_config,
} = storeToRefs(extension_store)

/** 启停操作中的扩展 id */
const toggling = ref('')
const config_open = ref(false)
const active_extension = ref(null)
/** 当前配置弹窗所示扩展 id：列表刷新（如语言切换）后据此同步名称 / 描述 */
const active_extension_id = ref('')

// 语言切换后 installed_list 会重新下发（名称 / 描述按新语言），同步弹窗内的展示信息
watch(
  () => installed_list.value,
  (list) => {
    if (!active_extension_id.value) return
    const matched = list.find((item) => item.id === active_extension_id.value)
    if (matched) active_extension.value = matched
  },
)

/** 拉取已安装扩展列表（父级刷新后也会调用） */
async function refresh_installed({ silent = false } = {}) {
  await run(
    () => extension_store.fetch_installed({ silent }),
    t('extensions.installed_fetch_list_failed'),
  )
}

onMounted(() => {
  // 列表已由父级并行加载时为静默刷新，避免重复闪 loading
  refresh_installed({ silent: installed_list.value.length > 0 })
})

/** 是否有配置项（决定是否显示配置按钮） */
function has_config(extension) {
  const properties = extension.config_schema?.properties || {}
  return Object.keys(properties).length > 0
}

async function toggle_extension(extension, enabled) {
  toggling.value = extension.id
  try {
    await extension_store.set_enabled(extension.id, enabled)
    toast.success(
      enabled
        ? t('extensions.installed_enable_success', { name: extension.name })
        : t('extensions.installed_disable_success', { name: extension.name }),
    )
    ask_restart(t('extensions.installed_toggle_restart_prompt', { name: extension.name }))
  } catch (error) {
    toast.error(error.message || t('extensions.installed_toggle_failed'))
  } finally {
    toggling.value = ''
  }
}

async function uninstall_extension(extension) {
  const task = await submit_task(
    () => extension_store.uninstall_extension(extension.id),
    t('extensions.installed_uninstall_failed'),
  )
  if (task) {
    emit('changed')
    toast.success(t('extensions.installed_uninstall_success', { name: extension.name }))
  }
}

async function open_config(extension) {
  active_extension_id.value = extension.id
  active_extension.value = extension
  config_open.value = true
  try {
    await Promise.all([
      extension_store.fetch_detail(extension.id),
      extension_store.fetch_config(extension.id),
    ])
  } catch (error) {
    toast.error(error.message || t('extensions.config_fetch_failed'))
  }
}

async function save_extension_config(values) {
  try {
    await extension_store.save_config(active_extension_id.value, values)
    toast.success(t('extensions.config_save_success', { name: active_extension.value?.name }))
    config_open.value = false
  } catch (error) {
    toast.error(error.message || t('extensions.config_save_failed'))
  }
}

/** 卡片是否启用（loaded / enabled 视为开启） */
function is_enabled(extension) {
  return extension.state === 'enabled' || extension.state === 'loaded'
}
</script>

<template>
  <div>
    <div v-if="loading" class="card">
      <div class="loading-block">
        <Spinner :size="18" /> {{ t('extensions.installed_loading') }}
      </div>
    </div>
    <EmptyState
      v-else-if="installed_list.length === 0"
      icon="lucide:puzzle"
      :title="t('extensions.installed_empty_title')"
      :description="t('extensions.installed_empty_description')"
    />
    <div v-else class="extension-grid">
      <article v-for="extension in installed_list" :key="extension.id" class="extension-card card">
        <div class="extension-head">
          <div class="extension-icon"><Icon icon="lucide:package" width="18" /></div>
          <div class="extension-title">
            <h3>{{ extension.name }}</h3>
            <span class="extension-id mono">{{ extension.id }}</span>
          </div>
          <div class="extension-badges">
            <Badge v-if="extension.builtin" variant="neutral">
              {{ t('extensions.installed_builtin_badge') }}
            </Badge>
            <Badge v-for="badge in type_badges(extension)" :key="badge.value" variant="accent">
              {{ badge.label }}
            </Badge>
            <Badge :variant="state_variant(extension.state)">
              {{ state_label(extension.state) }}
            </Badge>
          </div>
        </div>

        <div class="extension-desc">
          <p>{{ extension.description || t('extensions.installed_no_description') }}</p>
          <p v-if="extension.failure_reason" class="extension-reason">
            {{ extension.failure_reason }}
          </p>
        </div>

        <div class="extension-foot">
          <div class="extension-meta">
            <span class="mono">v{{ extension.version }}</span>
            <span v-if="extension.author" class="text-muted">· {{ extension.author }}</span>
          </div>
          <div class="extension-actions">
            <Button
              v-if="has_config(extension)"
              variant="ghost"
              size="sm"
              :title="t('extensions.installed_config_action')"
              :disabled="!auth_store.is_admin"
              @click="open_config(extension)"
            >
              <Icon icon="lucide:settings-2" width="14" />
              {{ t('extensions.installed_config_action') }}
            </Button>
            <Button
              v-if="!extension.builtin"
              variant="ghost"
              size="sm"
              class="danger"
              :title="t('extensions.installed_uninstall_action')"
              :disabled="!auth_store.is_admin"
              @click="uninstall_extension(extension)"
            >
              <Icon icon="lucide:trash-2" width="14" />
            </Button>
            <Switch
              :model-value="is_enabled(extension)"
              :disabled="!auth_store.is_admin || toggling === extension.id"
              @update:model-value="(value) => toggle_extension(extension, value)"
            />
          </div>
        </div>
      </article>
    </div>

    <ExtensionConfigDialog
      v-model="config_open"
      :extension="active_extension"
      :schema="detail?.config_schema"
      :values="config_values"
      :loading="detail_loading || config_loading"
      :saving="saving_config"
      @save="save_extension_config"
    />
  </div>
</template>

<style scoped>
.extension-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.extension-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-3);
}

.extension-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.extension-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.extension-title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.extension-title h3 {
  font-size: var(--text-sm);
  font-weight: 600;
}

.extension-id {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.extension-badges {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
}

.extension-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  flex: 1;
}

.extension-desc p {
  margin: 0;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.extension-reason {
  margin-top: var(--space-1);
  color: var(--warning);
  font-size: var(--text-xs);
  line-height: 1.4;
}

.extension-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}

.extension-meta,
.extension-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
}

.extension-actions {
  gap: var(--space-2);
}

.extension-actions .danger {
  color: var(--danger);
}

.extension-actions .danger:hover {
  background: var(--danger-soft);
}
</style>
