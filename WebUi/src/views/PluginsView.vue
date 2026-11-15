<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { usePluginStore } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_restart } from '@/composables/use_restart'
import { use_task_submit } from '@/composables/use_task_submit'
import Tabs from '@/components/ui/Tabs.vue'
import Badge from '@/components/ui/Badge.vue'
import Switch from '@/components/ui/Switch.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import MarketPanel from '@/components/MarketPanel.vue'

const plugin_store = usePluginStore()
const auth_store = useAuthStore()
const { t } = useI18n()
const toast = use_toast()
const { ask_restart } = use_restart()
const { submit_task, maybe_ask_restart } = use_task_submit()
const {
  installed_list,
  registered_plugin_modules,
  market_items,
  market_total,
  market_page,
  market_page_size,
  loading,
  market_loading,
} = storeToRefs(plugin_store)

const active_tab = ref('installed')
const market_keyword = ref('')
const toggling = ref('')
const removing_item = ref('')
const market_action = ref('')

const tabs = computed(() => [
  { value: 'installed', label: t('plugins.tab_installed'), icon: 'lucide:puzzle' },
  { value: 'market', label: t('plugins.tab_market'), icon: 'lucide:store' },
])

const hint = computed(() => t('plugins.market_hint'))

const type_labels = computed(() => ({
  builtin: t('plugins.type_builtin'),
  dependency: t('plugins.type_dependency'),
  external: t('plugins.type_external'),
}))

onMounted(() => {
  refresh_installed()
  plugin_store
    .fetch_registered_plugins()
    .catch((error) => console.warn('fetch_registered_plugins failed', error))
  search_market()
})

async function refresh_installed() {
  try {
    await plugin_store.fetch_installed()
  } catch (error) {
    toast.error(error.message || t('plugins.fetch_list_failed'))
  }
}

async function toggle_plugin(plugin, enabled) {
  const display_name = plugin.display_name || plugin.name
  toggling.value = plugin.name
  try {
    await plugin_store.set_enabled(plugin.name, enabled)
    toast.success(
      enabled
        ? t('plugins.enable_success', { name: display_name })
        : t('plugins.disable_success', { name: display_name }),
    )
    ask_restart(t('plugins.restart_after_toggle_confirm', { name: display_name }))
  } catch (error) {
    toast.error(error.message || t('plugins.toggle_failed'))
  } finally {
    toggling.value = ''
  }
}

function can_remove_plugin(plugin) {
  return plugin.type !== 'builtin' && registered_plugin_modules.value.includes(plugin.module_name)
}

async function remove_plugin(plugin) {
  const display_name = plugin.display_name || plugin.name
  removing_item.value = plugin.module_name
  const task = await submit_task(
    () => plugin_store.remove_plugin(plugin.module_name),
    t('plugins.remove_failed'),
  )
  removing_item.value = ''
  if (task) {
    toast.success(t('plugins.remove_success', { name: display_name }))
    // 依赖卸载完成后才询问是否重启（task.result.restart_required 由后端标记）
    maybe_ask_restart(task, t('plugins.restart_after_remove_confirm', { name: display_name }))
  }
}

async function search_market() {
  try {
    await plugin_store.fetch_market({ page: 1, keyword: market_keyword.value.trim() })
  } catch (error) {
    toast.error(error.message || t('plugins.fetch_market_failed'))
  }
}

async function go_market_page(page) {
  try {
    await plugin_store.go_market_page(page)
  } catch (error) {
    toast.error(error.message || t('plugins.load_page_failed'))
  }
}

async function install_market_plugin(item) {
  market_action.value = item.module_name
  const task = await submit_task(
    () => plugin_store.install_plugin(item.project_link),
    t('plugins.install_failed'),
  )
  market_action.value = ''
  if (task) {
    toast.success(t('plugins.install_success', { name: item.name }))
    await refresh_after_market_action()
    maybe_ask_restart(task, t('plugins.restart_after_install_confirm', { name: item.name }))
  }
}

async function upgrade_market_plugin(item) {
  market_action.value = item.module_name
  const task = await submit_task(
    () => plugin_store.upgrade_plugin(item.project_link),
    t('plugins.upgrade_failed'),
  )
  market_action.value = ''
  if (task) {
    toast.success(t('plugins.upgrade_success', { name: item.name }))
    await refresh_after_market_action()
    maybe_ask_restart(task, t('plugins.restart_after_upgrade_confirm', { name: item.name }))
  }
}

async function refresh_after_market_action() {
  await Promise.all([plugin_store.fetch_installed(), plugin_store.fetch_registered_plugins()])
  await plugin_store.fetch_market({ keyword: market_keyword.value.trim() })
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('plugins.page_title') }}</h1>
        <p class="page-desc">{{ t('plugins.page_description') }}</p>
      </div>
    </div>

    <Tabs v-model="active_tab" :tabs="tabs">
      <template #installed>
        <div v-if="loading" class="card">
          <div class="loading-block"><Spinner :size="18" /> {{ t('common.loading') }}</div>
        </div>
        <p v-else-if="installed_list.length === 0" class="plugin-empty-hint">
          {{ t('plugins.empty_installed') }}
        </p>
        <div v-else class="plugin-grid">
          <article v-for="plugin in installed_list" :key="plugin.name" class="plugin-card card">
            <div class="plugin-head">
              <div class="plugin-icon"><Icon icon="lucide:puzzle" width="18" /></div>
              <div class="plugin-title">
                <h3>{{ plugin.display_name || plugin.name }}</h3>
                <span class="plugin-name mono">{{ plugin.name }}</span>
              </div>
              <Badge variant="neutral">{{ type_labels[plugin.type] || plugin.type }}</Badge>
            </div>

            <p class="plugin-desc">{{ plugin.description || t('plugins.no_description') }}</p>

            <div class="plugin-foot">
              <div class="plugin-meta">
                <span class="mono">{{ plugin.version }}</span>
                <span class="text-muted">· {{ plugin.author || t('plugins.unknown_author') }}</span>
              </div>
              <div class="plugin-actions">
                <Switch
                  :model-value="plugin.enabled"
                  :disabled="
                    !plugin.can_disable || !auth_store.is_admin || toggling === plugin.name
                  "
                  @update:model-value="(value) => toggle_plugin(plugin, value)"
                />
                <Button
                  v-if="can_remove_plugin(plugin)"
                  variant="ghost"
                  size="sm"
                  icon-only
                  :title="t('plugins.remove_button_title')"
                  :disabled="!auth_store.is_admin || Boolean(removing_item)"
                  :loading="removing_item === plugin.module_name"
                  @click="remove_plugin(plugin)"
                >
                  <Icon icon="lucide:trash-2" width="15" />
                </Button>
              </div>
            </div>
          </article>
        </div>
      </template>

      <template #market>
        <MarketPanel
          :model-value="market_keyword"
          :items="market_items"
          :loading="market_loading"
          :placeholder="t('plugins.search_placeholder')"
          :hint="hint"
          :total="market_total"
          :page="market_page"
          :page-size="market_page_size"
          :busy="market_action"
          :show-actions="auth_store.is_admin"
          @update:model-value="(value) => (market_keyword = value)"
          @search="search_market"
          @page-change="go_market_page"
          @install="install_market_plugin"
          @upgrade="upgrade_market_plugin"
        />
      </template>
    </Tabs>
  </div>
</template>

<style scoped>
.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.plugin-empty-hint {
  padding: var(--space-6) 0;
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.plugin-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-3);
}

.plugin-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.plugin-icon {
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

.plugin-title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.plugin-title h3 {
  font-size: var(--text-sm);
  font-weight: 600;
}

.plugin-name {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plugin-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.plugin-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}

.plugin-meta,
.plugin-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
}
</style>
