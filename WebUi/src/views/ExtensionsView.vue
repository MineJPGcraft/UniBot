<script setup>
/**
 * 扩展管理页面骨架。
 *
 * 三个页签各自封装为 `components/extensions/*Panel.vue`：
 * - `InstalledExtensionsPanel`：已安装扩展卡片网格 + 配置弹窗；
 * - `ExtensionMarketPanel`：扩展市场（安装 / 升级 / 切换历史版本）；
 * - `RenderSettingsPanel`：渲染引擎、模板与插件配置。
 *
 * 头部动作（热重载、Studio 启动 / 停止 / 日志）分别由页面与 `StudioActions` 承担；
 * 由于页签切换会卸载非活动面板，重载 / 安装 / 卸载后的列表刷新统一在 store 层调用。
 */
import { computed, onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { useExtensionStore } from '@/stores/extension'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_task_submit } from '@/composables/use_task_submit'
import Button from '@/components/ui/Button.vue'
import Tabs from '@/components/ui/Tabs.vue'
import InstalledExtensionsPanel from '@/components/extensions/InstalledExtensionsPanel.vue'
import ExtensionMarketPanel from '@/components/extensions/ExtensionMarketPanel.vue'
import RenderSettingsPanel from '@/components/extensions/RenderSettingsPanel.vue'
import StudioActions from '@/components/extensions/StudioActions.vue'

const { t } = useI18n()
const extension_store = useExtensionStore()
const config_store = useConfigStore()
const auth_store = useAuthStore()
const toast = use_toast()
const { submit_task } = use_task_submit()

const active_tab = ref('installed')
/** 重新加载扩展操作中的标志 */
const reloading = ref(false)

const tabs = computed(() => [
  { value: 'installed', label: t('extensions.tab_installed'), icon: 'lucide:puzzle' },
  { value: 'market', label: t('extensions.tab_market'), icon: 'lucide:store' },
  { value: 'render', label: t('extensions.tab_render'), icon: 'lucide:image' },
])

onMounted(async () => {
  const results = await Promise.allSettled([
    config_store.config_data ? Promise.resolve() : config_store.fetch_all(),
    extension_store.fetch_renderers(),
    extension_store.fetch_templates(),
    extension_store.fetch_render_configs(),
    extension_store.fetch_studio_status(),
  ])
  if (results.some((result) => result.status === 'rejected')) {
    toast.error(t('extensions.load_partial_failed'))
  }
})

/** 热重载全部扩展：提交后台任务，进度在任务中心查看 */
async function reload_extensions() {
  reloading.value = true
  try {
    const task = await submit_task(() => extension_store.reload(), t('extensions.reload_failed'))
    if (!task) return
    // 页签切换会卸载对应面板，此处直接刷新 store，保证任意页签下都能同步列表
    await extension_store.fetch_installed({ silent: true })
    toast.success(t('extensions.reload_success'))
  } finally {
    reloading.value = false
  }
}

/** 市场安装 / 卸载后同步刷新已安装列表 */
async function refresh_after_change() {
  await extension_store.fetch_installed({ silent: true })
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('extensions.page_title') }}</h1>
        <p class="page-desc">{{ t('extensions.page_description') }}</p>
      </div>
      <div class="page-actions">
        <Button
          variant="ghost"
          :loading="reloading"
          :disabled="!auth_store.is_admin"
          :title="t('extensions.reload_button_title')"
          @click="reload_extensions"
        >
          <Icon icon="lucide:refresh-cw" width="16" />
          {{ t('extensions.reload_button') }}
        </Button>
        <!-- Studio 停止 / 日志 / 启动：按钮与弹窗内聚在子组件 -->
        <StudioActions />
      </div>
    </div>

    <Tabs v-model="active_tab" :tabs="tabs">
      <template #installed>
        <InstalledExtensionsPanel @changed="refresh_after_change" />
      </template>

      <template #market>
        <ExtensionMarketPanel @changed="refresh_after_change" />
      </template>

      <template #render>
        <RenderSettingsPanel />
      </template>
    </Tabs>
  </div>
</template>
