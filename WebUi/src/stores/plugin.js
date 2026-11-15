/**
 * 插件 Store：已安装插件与插件市场
 *
 * 安装/升级/卸载都涉及依赖变更（uv add / uv remove），后端以任务中心任务执行，
 * 接口立即返回任务快照。等待任务结束与重启询问统一交给
 * `composables/use_task_submit.js`，本 store 只负责请求与列表刷新。
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const usePluginStore = defineStore('plugin', () => {
  const installed_list = ref([])
  const registered_plugin_modules = ref([])
  const market_items = ref([])
  const market_total = ref(0)
  const market_page = ref(1)
  const market_page_size = ref(20)
  const loading = ref(false)
  const market_loading = ref(false)

  /** 获取已安装插件列表；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_installed({ silent = false } = {}) {
    if (!silent) loading.value = true
    try {
      installed_list.value = (await http.get('/api/plugins')) || []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function set_enabled(name, enabled) {
    await http.post(
      `/api/plugins/${encodeURIComponent(name)}/${enabled ? 'enable' : 'disable'}`,
      {},
    )
    await fetch_installed()
  }

  /** 提交卸载任务并刷新列表，返回任务快照 */
  async function remove_plugin(module_name) {
    const task = await http.delete(`/api/plugins/${encodeURIComponent(module_name)}`)
    await Promise.all([fetch_installed(), fetch_registered_plugins()])
    return task
  }

  async function fetch_registered_plugins() {
    const data = await http.get('/api/config/nonebot')
    registered_plugin_modules.value = (data.plugins || []).map((plugin) => plugin.module_name)
  }

  async function fetch_market({ page = 1, page_size = 20, keyword = '', category = '' } = {}) {
    market_loading.value = true
    try {
      const data = await http.get('/api/plugins/market', {
        query: { page, page_size, keyword, category },
      })
      market_items.value = data.items
      market_total.value = data.total
      market_page.value = data.page || page
      market_page_size.value = data.page_size || page_size
    } finally {
      market_loading.value = false
    }
  }

  async function go_market_page(page) {
    await fetch_market({ page, page_size: market_page_size.value })
  }

  /** 从市场安装插件：提交后台任务并刷新列表，返回任务快照 */
  async function install_plugin(name, version) {
    const task = await http.post('/api/plugins/market/install', { name, version })
    await Promise.all([fetch_installed(), fetch_registered_plugins()])
    return task
  }

  /** 升级已安装插件：提交后台任务并刷新列表，返回任务快照 */
  async function upgrade_plugin(name) {
    const task = await http.post('/api/plugins/market/upgrade', { name })
    await Promise.all([fetch_installed(), fetch_registered_plugins()])
    return task
  }

  return {
    installed_list,
    registered_plugin_modules,
    market_items,
    market_total,
    market_page,
    market_page_size,
    loading,
    market_loading,
    fetch_installed,
    set_enabled,
    remove_plugin,
    fetch_registered_plugins,
    fetch_market,
    go_market_page,
    install_plugin,
    upgrade_plugin,
  }
})
