<script setup>
/**
 * 配置中心页面骨架。
 *
 * 四个页签各自封装为 `components/config/Config*Panel.vue`：
 * - `ConfigTomlPanel`：Config.toml 分组表单 + 门控 + diff + 图片依赖引导；
 * - `ConfigEnvPanel`：.env 分组表单 + diff（改动需重启）；
 * - `ConfigMessagesPanel`：消息文本覆盖层；
 * - `ConfigExtensionsPanel`：扩展配置表单。
 *
 * 本文件只负责：页签切换、URL query 同步（tab / group / key / extension）、
 * 首屏数据加载，以及 Config.toml / .env 的源码编辑弹窗。
 */
import { defineAsyncComponent, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/config'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Tabs from '@/components/ui/Tabs.vue'
import ConfigTomlPanel from '@/components/config/ConfigTomlPanel.vue'
import ConfigEnvPanel from '@/components/config/ConfigEnvPanel.vue'
import ConfigMessagesPanel from '@/components/config/ConfigMessagesPanel.vue'
import ConfigExtensionsPanel from '@/components/config/ConfigExtensionsPanel.vue'

// 异步组件：CodeEditor 依赖整条 CodeMirror，仅源码编辑弹窗用到，
// 改为惰性加载，配置页挂载时不再阻塞路由切换。
const CodeEditor = defineAsyncComponent(() => import('@/components/ui/CodeEditor.vue'))

const config_store = useConfigStore()
const toast = use_toast()
const { ask_restart } = use_restart()
const {
  env_groups,
  raw_config,
  raw_env,
  raw_config_original,
  raw_env_original,
  raw_loading,
  raw_saving,
} = storeToRefs(config_store)

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const active_tab = ref(
  ['toml', 'env', 'messages', 'extensions'].includes(route.query.tab) ? route.query.tab : 'toml',
)
/** 当前环境变量分组（与 URL query.group 双向同步） */
const active_env_group = ref('')
/** 当前扩展配置 id（与 URL query.extension 双向同步） */
const active_extension_id = ref('')

const tabs = [
  { value: 'toml', label: 'Config.toml', icon: 'lucide:file-cog' },
  { value: 'env', label: t('config_view.tab_env'), icon: 'lucide:terminal' },
  { value: 'extensions', label: t('config_view.tab_extensions'), icon: 'lucide:puzzle' },
  { value: 'messages', label: t('config_view.tab_messages'), icon: 'lucide:message-square' },
]

// ---------- 源码编辑弹窗（Config.toml / .env 共用） ----------

const raw_editor_open = ref(false)
const raw_editor_target = ref('toml')
const raw_loaded = ref(false)

/** 按目标文件切换弹窗文案 */
const raw_editor_is_env = () => raw_editor_target.value === 'env'

const current_raw_changed = ref(false)

function sync_raw_changed() {
  current_raw_changed.value = raw_editor_is_env()
    ? raw_env.value !== raw_env_original.value
    : raw_config.value !== raw_config_original.value
}

watch(
  [raw_config, raw_env, raw_config_original, raw_env_original, raw_editor_target],
  sync_raw_changed,
)

/** 打开源码编辑弹窗（首次打开时按需拉取原始文本） */
async function open_raw_editor(target) {
  raw_editor_target.value = target
  raw_editor_open.value = true
  if (!raw_loaded.value) {
    raw_loaded.value = true
    try {
      await config_store.fetch_raw()
    } catch (error) {
      raw_loaded.value = false
      toast.error(error.message || t('config_view.toast_load_raw_failed'))
    }
  }
}

function reset_raw() {
  if (raw_editor_is_env()) {
    raw_env.value = raw_env_original.value
  } else {
    raw_config.value = raw_config_original.value
  }
}

async function confirm_raw_save() {
  try {
    const { saved_toml, saved_env } = await config_store.save_raw()
    if (raw_editor_is_env()) {
      if (saved_env) {
        toast.success(t('config_view.toast_raw_env_saved'))
        ask_restart(t('config_view.restart_env_changed'))
      } else {
        toast.success(t('config_view.no_changes_detected'))
      }
    } else {
      toast.success(
        saved_toml ? t('config_view.toast_raw_toml_saved') : t('config_view.no_changes_detected'),
      )
    }
    raw_editor_open.value = false
  } catch (error) {
    toast.error(error.message || t('config_view.save_failed'))
  }
}

// ---------- URL query 同步 ----------

function sync_query(patch) {
  const query = { ...route.query, ...patch }
  // 非当前 tab 的 group / extension 信息不保留
  if (patch.tab && patch.tab !== 'env') delete query.group
  if (patch.tab && patch.tab !== 'extensions') delete query.extension
  router.replace({ query })
}

watch(active_tab, (value) => {
  sync_query({ tab: value })
})

watch(active_env_group, (value) => {
  if (active_tab.value === 'env' && value) sync_query({ group: value })
})

watch(active_extension_id, (value) => {
  if (active_tab.value === 'extensions' && value) sync_query({ extension: value })
})

// ---------- 首屏加载 ----------

/** 依据 URL query 定位 .env 分组（group 优先，其次按 key 反查） */
function resolve_env_group() {
  const query_group = route.query.group
  if (typeof query_group === 'string' && query_group) return query_group
  const query_key = route.query.key
  if (typeof query_key !== 'string') return ''
  const matched = env_groups.value.find((group) => group.keys.includes(query_key))
  return matched ? matched.id : ''
}

async function load() {
  try {
    await config_store.fetch_all()
  } catch (error) {
    toast.error(error.message || t('config_view.toast_fetch_failed'))
  }
  try {
    await config_store.fetch_env()
    active_env_group.value = resolve_env_group()
  } catch {
    // 环境变量加载失败不阻塞页面
  }
}

load()
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('config_view.page_title') }}</h1>
        <p class="page-desc">{{ t('config_view.page_desc') }}</p>
      </div>
    </div>

    <Tabs v-model="active_tab" :tabs="tabs">
      <!-- Config.toml 配置 -->
      <template #toml>
        <ConfigTomlPanel @edit-source="open_raw_editor('toml')" />
      </template>

      <!-- 环境变量 -->
      <template #env>
        <ConfigEnvPanel v-model="active_env_group" @edit-source="open_raw_editor('env')" />
      </template>

      <!-- 消息文本 -->
      <template #messages>
        <ConfigMessagesPanel />
      </template>

      <!-- 扩展配置 -->
      <template #extensions>
        <ConfigExtensionsPanel v-model="active_extension_id" />
      </template>
    </Tabs>

    <!-- 源码编辑弹窗：按当前 tab 编辑对应文件的原始文本 -->
    <Dialog
      v-model="raw_editor_open"
      :title="
        raw_editor_is_env()
          ? t('config_view.tab_raw_title_env')
          : t('config_view.tab_raw_title_toml')
      "
      :description="
        raw_editor_is_env() ? t('config_view.tab_raw_desc_env') : t('config_view.tab_raw_desc_toml')
      "
      :confirm-text="t('config_view.save_changes')"
      :loading="raw_saving"
      width="70vw"
      @confirm="confirm_raw_save"
    >
      <div v-if="raw_loading" class="raw-loading">
        <Spinner />
        <span>{{ t('config_view.tab_raw_loading') }}</span>
      </div>
      <template v-else>
        <div class="raw-field">
          <label class="raw-label">
            <Icon :icon="raw_editor_is_env() ? 'lucide:terminal' : 'lucide:file-cog'" width="14" />
            {{ raw_editor_is_env() ? '.env' : 'Config.toml' }}
          </label>
          <CodeEditor
            v-if="raw_editor_is_env()"
            v-model="raw_env"
            language="properties"
            class="raw-code-editor raw-code-editor--env"
          />
          <CodeEditor v-else v-model="raw_config" language="toml" class="raw-code-editor" />
        </div>
      </template>
      <div class="raw-actions">
        <span v-if="current_raw_changed" class="raw-changed">
          <Icon icon="lucide:circle-alert" width="13" />
          {{ t('config_view.changed_tip') }}
        </span>
        <span v-else class="raw-saved-tip">
          <Icon icon="lucide:check" width="13" />
          {{ t('config_view.unchanged_tip') }}
        </span>
        <div class="raw-actions-right">
          <Button
            variant="secondary"
            size="sm"
            :disabled="raw_loading || !current_raw_changed"
            @click="reset_raw"
          >
            <Icon icon="lucide:rotate-ccw" width="14" />
            {{ t('config_view.tab_raw_restore') }}
          </Button>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
/* 源码编辑弹窗 */
.raw-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-10) 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.raw-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.raw-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.raw-code-editor {
  height: 480px;
}

.raw-code-editor--env {
  height: 360px;
}

.raw-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.raw-changed {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--warning);
}

.raw-saved-tip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.raw-actions-right {
  display: flex;
  gap: var(--space-2);
}

@media (max-width: 700px) {
  .raw-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .raw-actions-right {
    justify-content: flex-end;
  }
}
</style>
