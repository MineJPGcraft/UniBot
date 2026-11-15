<script setup>
/**
 * 配置中心：图片模式依赖扩展引导弹窗。
 *
 * 图片模式（`image.mode`）开启后，后端要求 Html2Pic / Default 等渲染扩展已安装；
 * 本组件检查缺失项并分类展示：可自动下载、市场有该扩展但无兼容版本、市场未收录。
 * 暴露 `prompt()`：检查并弹窗，返回是否弹出了对话框（供调用方决定是否继续提示重启）。
 */
import { computed, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { useExtensionStore } from '@/stores/extension'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'
import Dialog from '@/components/ui/Dialog.vue'

const { t } = useI18n()
const extension_store = useExtensionStore()
const toast = use_toast()
const { ask_restart } = use_restart()

const open = ref(false)
/** 市场有兼容版本、可自动下载的缺失项 */
const missing_items = ref([])
/** 市场有该扩展但无兼容当前核心版本的缺失项 */
const unsupported_items = ref([])
/** 市场未收录的缺失项 */
const not_in_market_items = ref([])
const installing = ref(false)

const confirm_text = computed(() =>
  missing_items.value.length > 0
    ? t('config_view.image_deps_confirm_install')
    : t('config_view.image_deps_confirm_ok'),
)

/** 检查图片模式依赖扩展，缺失时弹窗询问是否自动下载；返回是否弹出了对话框 */
async function prompt() {
  try {
    const requirements = await extension_store.fetch_image_requirements()
    const missing = (requirements?.required || []).filter((item) => !item.installed)
    if (missing.length === 0) return false
    // 市场有兼容版本 → 可自动安装；有该扩展但无兼容版本 → 提示不支持；否则 → 提示手动安装
    missing_items.value = missing.filter((item) => item.in_market && !item.unsupported)
    unsupported_items.value = missing.filter((item) => item.in_market && item.unsupported)
    not_in_market_items.value = missing.filter((item) => !item.in_market)
    open.value = true
    return true
  } catch (error) {
    toast.error(error.message || t('config_view.toast_check_image_deps_failed'))
    return false
  }
}

/** 从市场自动下载缺失的图片模式依赖扩展，完成后提示重启 */
async function install_missing() {
  installing.value = true
  try {
    for (const item of missing_items.value) {
      await extension_store.install_market(item.id)
    }
    open.value = false
    toast.success(t('config_view.toast_image_deps_downloaded'))
    ask_restart(t('config_view.restart_image_deps'))
  } catch (error) {
    toast.error(error.message || t('config_view.toast_download_extension_failed'))
  } finally {
    installing.value = false
  }
}

/** 确认：无可自动下载项时仅关闭 */
async function confirm() {
  if (missing_items.value.length === 0) {
    open.value = false
    return
  }
  await install_missing()
}

defineExpose({ prompt })
</script>

<template>
  <Dialog
    v-model="open"
    :title="t('config_view.image_deps_title')"
    :description="t('config_view.image_deps_desc')"
    :confirm-text="confirm_text"
    :cancel-text="t('config_view.image_deps_cancel_later')"
    :loading="installing"
    @confirm="confirm"
  >
    <div class="image-deps-list">
      <div v-for="item in missing_items" :key="item.id" class="image-dep-item">
        <Icon icon="lucide:download" width="15" class="text-muted" />
        <span>{{ item.name }}</span>
        <span class="mono text-muted">{{ item.id }}</span>
      </div>
      <div v-if="unsupported_items.length > 0" class="image-dep-warning">
        <Icon icon="lucide:shield-alert" width="15" />
        <span>
          {{ t('config_view.image_deps_unsupported_warning') }}
          <span v-for="item in unsupported_items" :key="item.id" class="mono image-dep-inline">
            {{ t('config_view.image_deps_item_with_id', { name: item.name, id: item.id }) }}
          </span>
        </span>
      </div>
      <div v-if="not_in_market_items.length > 0" class="image-dep-warning">
        <Icon icon="lucide:triangle-alert" width="15" />
        <span>
          {{ t('config_view.image_deps_not_in_market_warning') }}
          <span v-for="item in not_in_market_items" :key="item.id" class="mono image-dep-inline">
            {{ t('config_view.image_deps_item_with_id', { name: item.name, id: item.id }) }}
          </span>
        </span>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.image-deps-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.image-dep-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--surface-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: var(--text-sm);
}

.image-dep-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--warning-soft, rgb(250 204 21 / 0.1));
  border: 1px solid var(--warning, #ca8a04);
  border-radius: var(--radius);
  color: var(--warning, #ca8a04);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.image-dep-inline {
  margin-left: var(--space-1);
}
</style>
