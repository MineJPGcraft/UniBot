<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/config'
import { useAdapterStore } from '@/stores/adapter'
import { useStatusStore } from '@/stores/status'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import McConnectDialog from '@/components/McConnectDialog.vue'

const { t } = useI18n()
const router = useRouter()
const config_store = useConfigStore()
const adapter_store = useAdapterStore()
const status_store = useStatusStore()
const auth_store = useAuthStore()
const toast = use_toast()
const { status } = storeToRefs(status_store)
const { env_values } = storeToRefs(config_store)

/** 引导数据加载中，避免初次渲染时步骤状态闪烁 */
const ready = ref(false)

/** 令牌授权提示框状态 */
const token_dialog_open = ref(false)
const token_loading = ref(false)
const token_value = ref('')

/** MC 服务器接入配置提示框状态 */
const mc_connect_open = ref(false)

async function open_token_dialog() {
  token_dialog_open.value = true
  token_value.value = ''
  token_loading.value = true
  try {
    token_value.value = await status_store.fetch_token()
  } catch (error) {
    toast.error(error.message || t('setup.setup_fetch_token_failed'))
  } finally {
    token_loading.value = false
  }
}

async function copy_token() {
  if (!token_value.value) return
  try {
    await navigator.clipboard.writeText(token_value.value)
    toast.success(t('setup.setup_token_copied'))
  } catch {
    toast.error(t('common.copy_failed'))
  }
}

/**
 * 已加载的聊天平台适配器（排除 Minecraft 适配器）
 * adapters 为适配器注册名（由后端 get_adapters().keys() 提供，如 “Minecraft”），不是模块路径
 */
const chat_ready = computed(() => {
  const adapters = status.value?.adapters || []
  return adapters.some((name) => !String(name).toLowerCase().includes('minecraft'))
})

/** 已接入 Minecraft 服务器（有在线服务器，或已配置 WS 地址） */
const server_ready = computed(() => {
  if (Number(status.value?.servers_online || 0) > 0) return true
  const value = env_values.value?.MINECRAFT_WS_URLS
  if (!value) return false
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return true
})

/** 引导折叠状态，持久化到 localStorage */
const collapsed_key = 'unibot_setup_guide_collapsed'
const collapsed = ref(localStorage.getItem(collapsed_key) === '1')

/**
 * 快速开始引导仅对管理员展示：其中「快速授权令牌」等步骤涉及管理员专属接口，
 * 非管理员看得到却点不动，故整块引导统一隐藏。
 */
const is_admin = computed(() => auth_store.is_admin)

function toggle_collapsed() {
  collapsed.value = !collapsed.value
  localStorage.setItem(collapsed_key, collapsed.value ? '1' : '0')
}

/** 已配置超级用户（SUPERUSERS 非空） */
const superuser_ready = computed(() => {
  const value = env_values.value?.SUPERUSERS
  return Array.isArray(value) ? value.length > 0 : Boolean(value)
})

const steps = computed(() => [
  {
    key: 'chat',
    title_key: 'setup.setup_step_chat_title',
    description_key: 'setup.setup_step_chat_description',
    icon: 'lucide:message-circle',
    done: chat_ready.value,
    target: { path: '/adapters' },
  },
  {
    key: 'server',
    title_key: 'setup.setup_step_server_title',
    description_key: 'setup.setup_step_server_description',
    icon: 'lucide:server',
    action_label_key: 'setup.setup_step_server_action',
    done: server_ready.value,
  },
  // 整块引导仅管理员可见（见模板 v-if），故令牌步骤对所有可见者都适用
  {
    key: 'superuser',
    title_key: 'setup.setup_step_superuser_title',
    description_key: 'setup.setup_step_superuser_description',
    icon: 'lucide:shield',
    action_label_key: 'setup.setup_step_superuser_action',
    done: superuser_ready.value,
    target: { name: 'ConfigView', query: { tab: 'env', group: 'framework' } },
  },
])

const done_count = computed(() => steps.value.filter((step) => step.done).length)
const all_done = computed(() => steps.value.length > 0 && done_count.value === steps.value.length)

function go(step) {
  if (step.key === 'superuser') {
    open_token_dialog()
    return
  }
  if (step.key === 'server') {
    mc_connect_open.value = true
    return
  }
  if (typeof step.target === 'string') {
    window.open(step.target, '_blank', 'noopener')
    return
  }
  router.push(step.target)
}

onMounted(async () => {
  await Promise.allSettled([
    config_store.fetch_env(),
    adapter_store.fetch_all(),
    status_store.fetch_status(),
  ])
  ready.value = true
})
</script>

<template>
  <!-- 整块引导仅管理员可见：含管理员专属的令牌步骤，非管理员一律不渲染 -->
  <div v-if="is_admin">
    <section v-if="ready && !all_done" class="setup-guide card">
      <div class="setup-head">
        <div class="setup-title">
          <span class="setup-icon"><Icon icon="lucide:rocket" width="16" /></span>
          <div>
            <h3 class="card-title">{{ t('setup.setup_title') }}</h3>
            <p class="setup-desc">{{ t('setup.setup_desc') }}</p>
          </div>
        </div>
        <div class="setup-actions">
          <div class="setup-progress">
            <span class="setup-count mono">{{ done_count }} / {{ steps.length }}</span>
            <Progress v-if="!collapsed" :value="done_count" :max="steps.length" class="setup-bar" />
          </div>
          <button
            class="setup-collapse"
            type="button"
            :title="collapsed ? t('setup.setup_expand') : t('setup.setup_collapse')"
            @click="toggle_collapsed"
          >
            <Icon :icon="collapsed ? 'lucide:chevron-down' : 'lucide:chevron-up'" width="16" />
          </button>
        </div>
      </div>

      <ol v-if="!collapsed" class="setup-steps">
        <li
          v-for="step in steps"
          :key="step.key"
          class="setup-step"
          :class="{ 'setup-step--done': step.done }"
          @click="go(step)"
        >
          <span class="setup-step-index">
            <Icon v-if="step.done" icon="lucide:check" width="13" />
            <Icon v-else :icon="step.icon" width="15" />
          </span>
          <div class="setup-step-body">
            <span class="setup-step-title">{{ t(step.title_key) }}</span>
            <span class="setup-step-desc">{{ t(step.description_key) }}</span>
          </div>
          <Badge :variant="step.done ? 'success' : 'neutral'">
            {{
              step.done
                ? t('setup.setup_step_done')
                : step.action_label_key
                  ? t(step.action_label_key)
                  : t('setup.setup_step_go_config')
            }}
          </Badge>
          <Icon icon="lucide:chevron-right" width="14" class="setup-arrow" />
        </li>
      </ol>
    </section>

    <Dialog
      v-model="token_dialog_open"
      :title="t('setup.setup_token_dialog_title')"
      :description="t('setup.setup_token_dialog_description')"
      :hide-footer="true"
      width="min(520px, calc(100vw - 32px))"
    >
      <div class="token-guide">
        <ol class="token-steps">
          <li>{{ t('setup.setup_token_step_copy') }}</li>
          <li>{{ t('setup.setup_token_step_send') }}</li>
          <li>{{ t('setup.setup_token_step_auto') }}</li>
        </ol>

        <div class="token-box">
          <div v-if="token_loading" class="token-loading">
            <Spinner :size="16" />
            {{ t('setup.setup_token_loading') }}
          </div>
          <template v-else>
            <code class="token-value mono">{{
              token_value || t('setup.setup_token_missing')
            }}</code>
            <Button variant="secondary" size="sm" :disabled="!token_value" @click="copy_token">
              <Icon icon="lucide:copy" width="14" />
              {{ t('common.copy') }}
            </Button>
          </template>
        </div>

        <p class="token-tip">
          {{ t('setup.setup_token_tip') }}
        </p>
      </div>
    </Dialog>

    <McConnectDialog v-model="mc_connect_open" />
  </div>
</template>

<style scoped>
.setup-guide {
  padding: var(--space-5);
  margin-bottom: var(--space-5);
}

.setup-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.setup-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.setup-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.setup-desc {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.setup-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.setup-progress {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.setup-count {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
}

.setup-bar {
  width: 120px;
  max-width: 30vw;
}

@media (max-width: 900px) {
  .setup-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .setup-steps {
    grid-template-columns: minmax(0, 1fr);
  }

  .setup-bar {
    display: none;
  }
}

.setup-collapse {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  transition:
    border-color var(--transition),
    color var(--transition);
}

.setup-collapse:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 步骤列表：minmax(0, 1fr) 防止 nowrap 文本把网格轨道撑出容器 */
.setup-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-4);
  list-style: none;
  padding: 0;
}

.setup-step {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  cursor: pointer;
  transition:
    border-color var(--transition),
    background-color var(--transition);
}

.setup-step:hover {
  border-color: var(--accent);
  background: var(--surface);
}

.setup-step--done {
  background: var(--success-soft);
  border-color: color-mix(in srgb, var(--success) 35%, transparent);
}

.setup-step--done:hover {
  border-color: var(--success);
}

.setup-step-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text-muted);
  flex-shrink: 0;
}

.setup-step--done .setup-step-index {
  background: var(--success);
  color: #fff;
}

.setup-step-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setup-step-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.setup-step-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setup-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 令牌授权提示框 */
.token-guide {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.token-steps {
  margin: 0;
  padding-left: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.token-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface-sunken);
}

.token-loading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.token-value {
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--accent);
  word-break: break-all;
}

.token-tip {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.6;
}
</style>
