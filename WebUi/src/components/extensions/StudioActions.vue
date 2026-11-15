<script setup>
/**
 * 扩展管理：Extension Studio 启动与日志弹窗。
 *
 * 页面头部按钮组（启动 / 打开 / 停止 / 查看日志）与两个弹窗都封装在此：
 * - 首次使用（尚未下载）时先弹「功能说明」对话框，确认后再下载启动；
 * - 启动成功后弹出独立窗口（同名窗口复用），失败按 `use_async_action` 提示；
 * - 日志弹窗按需拉取 Studio 输出。
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useExtensionStore } from '@/stores/extension'
import { useAuthStore } from '@/stores/auth'
import { use_async_action } from '@/composables/use_async_action'
import { use_toast } from '@/composables/use_toast'
import { Icon } from '@iconify/vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Spinner from '@/components/ui/Spinner.vue'

const { t } = useI18n()
const extension_store = useExtensionStore()
const auth_store = useAuthStore()
const toast = use_toast()
const { run } = use_async_action()
const { studio_status, studio_launching, studio_stopping, studio_log, studio_log_loading } =
  storeToRefs(extension_store)

/** 日志弹窗开关 */
const log_open = ref(false)
/** 首次下载说明弹窗开关 */
const intro_open = ref(false)

/** 启动创意工坊；首次使用（尚未下载）时先弹窗说明功能，由用户确认后再下载 */
function launch() {
  if (!studio_status.value?.installed) {
    intro_open.value = true
    return
  }
  start(false)
}

/** 用户在说明弹窗中确认后开始下载并启动 */
function confirm_launch() {
  intro_open.value = false
  start(true)
}

/** 下载（如缺失）并启动 Extension Studio，随后弹出独立窗口打开访问地址（含登录 token） */
async function start(will_download) {
  if (will_download) {
    toast.info(t('extensions.studio_download_started'))
  }
  let url = ''
  const ok = await run(
    () => extension_store.launch_studio().then((value) => (url = value)),
    t('extensions.studio_launch_failed'),
  )
  if (!ok) return
  if (url) {
    open_window(url)
    toast.success(t('extensions.studio_launch_window_success'))
  } else {
    toast.success(t('extensions.studio_launch_success'))
  }
}

/** 弹出独立窗口打开 Studio（复用同名窗口，避免重复弹窗） */
function open_window(url) {
  const width = Math.min(1280, window.screen.availWidth - 80)
  const height = Math.min(860, window.screen.availHeight - 80)
  const left = Math.max(0, Math.round((window.screen.availWidth - width) / 2))
  const top = Math.max(0, Math.round((window.screen.availHeight - height) / 2))
  const features = [
    `width=${width}`,
    `height=${height}`,
    `left=${left}`,
    `top=${top}`,
    'resizable=yes',
    'scrollbars=yes',
    'status=no',
  ].join(',')
  window.open(url, 'unibot-studio', features)
}

/** 停止 Extension Studio */
async function stop() {
  try {
    await extension_store.stop_studio()
    toast.success(t('extensions.studio_stop_success'))
  } catch (error) {
    toast.error(error.message || t('extensions.studio_stop_failed'))
  }
}

/** 打开日志弹窗并按需拉取输出 */
async function open_log() {
  log_open.value = true
  try {
    await extension_store.fetch_studio_log()
  } catch (error) {
    toast.error(error.message || t('extensions.studio_fetch_log_failed'))
  }
}
</script>

<template>
  <!-- 页面头部按钮组：停止 / 日志 / 启动 -->
  <Button
    v-if="studio_status?.running"
    variant="ghost"
    :loading="studio_stopping"
    :disabled="!auth_store.is_admin"
    :title="t('extensions.studio_stop_button_title')"
    @click="stop"
  >
    <Icon icon="lucide:square" width="16" />
    {{ t('extensions.studio_stop_button') }}
  </Button>
  <Button
    variant="ghost"
    :disabled="!studio_status?.installed"
    :title="t('extensions.studio_log_button_title')"
    @click="open_log"
  >
    <Icon icon="lucide:terminal" width="16" />
    {{ t('extensions.studio_log_button') }}
  </Button>
  <Button
    variant="primary"
    :loading="studio_launching"
    :disabled="!auth_store.is_admin"
    :title="t('extensions.studio_launch_button_title')"
    @click="launch"
  >
    <Icon icon="lucide:code-2" width="16" />
    {{
      studio_status?.running
        ? t('extensions.studio_open_button')
        : t('extensions.studio_launch_button')
    }}
  </Button>

  <!-- 首次下载说明 -->
  <Dialog
    v-model="intro_open"
    :title="t('extensions.studio_intro_dialog_title')"
    :description="t('extensions.studio_intro_dialog_description')"
    :confirm-text="t('extensions.studio_intro_confirm')"
    :loading="studio_launching"
    @confirm="confirm_launch"
  >
    <div class="studio-intro">
      <p>{{ t('extensions.studio_intro_body') }}</p>
      <ul>
        <li>{{ t('extensions.studio_intro_feature_design') }}</li>
        <li>{{ t('extensions.studio_intro_feature_testing') }}</li>
        <li>{{ t('extensions.studio_intro_feature_package') }}</li>
      </ul>
      <p>{{ t('extensions.studio_intro_download_prompt') }}</p>
    </div>
  </Dialog>

  <!-- Studio 日志 -->
  <Dialog
    v-model="log_open"
    :title="t('extensions.studio_log_dialog_title')"
    :description="t('extensions.studio_log_dialog_description')"
    :hide-footer="true"
    width="min(720px, calc(100vw - 32px))"
  >
    <div class="studio-log-box">
      <div v-if="studio_log_loading" class="studio-log-loading">
        <Spinner :size="16" /> {{ t('extensions.studio_log_loading') }}
      </div>
      <pre v-else-if="studio_log" class="studio-log-content">{{ studio_log }}</pre>
      <div v-else class="studio-log-empty">{{ t('extensions.studio_log_empty') }}</div>
    </div>
  </Dialog>
</template>

<style scoped>
/* 创意工坊首次下载说明弹窗 */
.studio-intro {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.studio-intro p {
  margin: 0 0 var(--space-2);
}

.studio-intro p:last-child {
  margin-bottom: 0;
}

.studio-intro ul {
  margin: 0 0 var(--space-2);
  padding-left: var(--space-5);
}

.studio-intro li {
  margin-bottom: var(--space-1);
}

/* Extension Studio 日志弹窗 */
.studio-log-box {
  max-height: 60vh;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-base);
}

.studio-log-content {
  margin: 0;
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}

.studio-log-loading,
.studio-log-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-6) 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
