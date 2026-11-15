<script setup>
/**
 * 扩展管理：扩展市场面板。
 *
 * 基于通用 `MarketPanel` 展示市场条目，并额外处理本地关键词过滤与「切换历史版本」
 * 的版本清单：安装 / 升级 / 切换版本都提交任务中心任务，等待任务结束后刷新列表。
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useExtensionStore } from '@/stores/extension'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import { use_task_submit } from '@/composables/use_task_submit'
import MarketPanel from '@/components/MarketPanel.vue'

const emit = defineEmits(['changed'])

const { t } = useI18n()
const extension_store = useExtensionStore()
const auth_store = useAuthStore()
const toast = use_toast()
const { run } = use_async_action()
const { submit_task } = use_task_submit()
const { market_items, market_loading } = storeToRefs(extension_store)

const keyword = ref('')
/** 已应用的关键词（点击搜索后生效） */
const applied_keyword = ref('')
/** 市场安装 / 升级操作中的扩展 id */
const action = ref('')
/** 版本清单菜单已打开的扩展 id / 正在加载的扩展 id */
const releases_for = ref('')
const releases_loading = ref('')
/** 当前扩展的可选版本（按版本倒序） */
const release_options = ref([])

/** 扩展市场本地搜索过滤（后端接口无搜索参数） */
const filtered_items = computed(() => {
  const keyword = applied_keyword.value.trim().toLowerCase()
  if (!keyword) return market_items.value
  return market_items.value.filter(
    (item) =>
      (item.name || '').toLowerCase().includes(keyword) ||
      (item.id || '').toLowerCase().includes(keyword) ||
      (item.description || '').toLowerCase().includes(keyword),
  )
})

/** 拉取市场列表（应用当前关键词） */
async function search() {
  applied_keyword.value = keyword.value
  await run(() => extension_store.fetch_market(), t('extensions.market_fetch_failed'))
}

/** 安装最新可用版本（version 为 null 表示自动选择兼容当前核心的版本） */
async function install(item) {
  await run_install(item, null)
}

/** 打开某扩展的版本清单下拉（再次点击关闭）；切换时清空上一次的版本列表 */
async function open_releases(item) {
  const extension_id = item.id
  if (releases_for.value === extension_id) {
    releases_for.value = ''
    return
  }
  releases_for.value = extension_id
  release_options.value = []
  releases_loading.value = extension_id
  try {
    const data = await extension_store.fetch_releases(extension_id)
    release_options.value = data?.releases || []
  } catch (error) {
    toast.error(error.message || t('extensions.market_versions_fetch_failed'))
  } finally {
    releases_loading.value = ''
  }
}

/** 切换到指定历史版本（显式指定版本时后端允许安装不兼容当前核心的版本） */
async function install_version(version) {
  const item = market_items.value.find((row) => row.id === releases_for.value)
  if (!item) return
  await run_install(item, version)
}

/** 提交安装任务，等待任务完成后刷新市场与已安装列表 */
async function run_install(item, version) {
  action.value = item.id
  releases_for.value = ''
  // 后端在任务中心串行完成下载 → 依赖同步 → 热重载，此处等任务结束并刷新列表
  const task = await submit_task(
    () => extension_store.install_market(item.id, version),
    t('extensions.installed_install_failed'),
  )
  action.value = ''
  if (!task) return
  await search()
  emit('changed')
  toast.success(
    version
      ? t('extensions.installed_version_switch_success', { name: item.name, version })
      : t('extensions.installed_install_success', { name: item.name }),
  )
}

// 市场条目在首次挂载时拉取（页签切换会重建组件，后端对无关键词请求带缓存）
onMounted(() => {
  search()
})
</script>

<template>
  <MarketPanel
    :model-value="keyword"
    :items="filtered_items"
    :loading="market_loading"
    :placeholder="t('extensions.market_view_search_placeholder')"
    :empty-title="t('extensions.market_view_empty_title')"
    :empty-description="t('extensions.market_view_empty_description')"
    item-icon="lucide:package"
    :busy="action"
    :show-actions="auth_store.is_admin"
    :version-switch="true"
    :releases-for="releases_for"
    :releases-loading="releases_loading"
    :releases="release_options"
    @update:model-value="(value) => (keyword = value)"
    @search="search"
    @install="install"
    @upgrade="install"
    @open-releases="open_releases"
    @install-version="install_version"
  />
</template>
