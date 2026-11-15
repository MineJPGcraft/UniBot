/**
 * 扩展 Store：已安装扩展、配置动态表单、渲染引擎与主题
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'
import { t_global } from '@/i18n'
import { useTaskStore } from '@/stores/task'

export const useExtensionStore = defineStore('extension', () => {
  const installed_list = ref([])
  const loading = ref(false)

  // 扩展详情 + 配置 schema
  const detail = ref(null)
  const detail_loading = ref(false)
  const config_values = ref({})
  const config_loading = ref(false)
  const saving_config = ref(false)

  // 渲染引擎与模板
  const renderers = ref([])
  const renderer_loading = ref(false)
  const templates = ref([])
  const template_loading = ref(false)

  // 渲染插件（渲染器 + 模板）配置，供渲染设置页内联编辑
  const render_configs = ref([])
  const render_config_loading = ref(false)
  const saving_render_config = ref('')

  // 全部扩展配置（含无代码模板包），供配置中心统一编辑
  const config_items = ref([])
  const config_items_loading = ref(false)
  const saving_config_item = ref('')

  // 扩展市场
  const market_items = ref([])
  const market_loading = ref(false)

  // 图片模式依赖扩展（渲染引擎 + 默认模板包）的下载情况
  const image_requirements = ref(null)
  const image_requirements_loading = ref(false)

  // Extension Studio（AI 扩展开发平台）
  const studio_status = ref(null)
  const studio_loading = ref(false)
  const studio_launching = ref(false)
  const studio_stopping = ref(false)
  const studio_log = ref('')
  const studio_log_loading = ref(false)

  /** 获取已安装扩展列表；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_installed({ silent = false } = {}) {
    if (!silent) loading.value = true
    try {
      installed_list.value = (await http.get('/api/extensions')) || []
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** 获取扩展详情；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_detail(extension_id, { silent = false } = {}) {
    if (!silent) detail_loading.value = true
    try {
      detail.value = await http.get(`/api/extensions/items/${encodeURIComponent(extension_id)}`)
    } finally {
      if (!silent) detail_loading.value = false
    }
  }

  /** 获取扩展配置；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_config(extension_id, { silent = false } = {}) {
    if (!silent) config_loading.value = true
    try {
      config_values.value =
        (await http.get(`/api/extensions/${encodeURIComponent(extension_id)}/config`)) || {}
    } finally {
      if (!silent) config_loading.value = false
    }
  }

  async function set_enabled(extension_id, enabled) {
    await http.post(
      `/api/extensions/${encodeURIComponent(extension_id)}/${enabled ? 'enable' : 'disable'}`,
      {},
    )
    await fetch_installed()
  }

  async function save_config(extension_id, values) {
    saving_config.value = true
    try {
      await http.patch(`/api/extensions/${encodeURIComponent(extension_id)}/config`, values)
      await fetch_config(extension_id)
    } finally {
      saving_config.value = false
    }
  }

  /** 获取渲染引擎列表；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_renderers({ silent = false } = {}) {
    if (!silent) renderer_loading.value = true
    try {
      renderers.value = (await http.get('/api/extensions/renderers')) || []
    } finally {
      if (!silent) renderer_loading.value = false
    }
  }

  async function switch_renderer(name) {
    await http.post('/api/extensions/renderers/switch', { name })
    await fetch_renderers()
  }

  /** 获取模板列表；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_templates({ silent = false } = {}) {
    if (!silent) template_loading.value = true
    try {
      templates.value = (await http.get('/api/extensions/templates')) || []
    } finally {
      if (!silent) template_loading.value = false
    }
  }

  async function switch_template(name) {
    await http.post('/api/extensions/templates/switch', { name })
    await fetch_templates()
  }

  /** 获取渲染插件配置列表；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_render_configs({ silent = false } = {}) {
    if (!silent) render_config_loading.value = true
    try {
      render_configs.value = (await http.get('/api/extensions/render-configs')) || []
    } finally {
      if (!silent) render_config_loading.value = false
    }
  }

  async function save_render_config(extension_id, values) {
    saving_render_config.value = extension_id
    try {
      await http.patch(`/api/extensions/${encodeURIComponent(extension_id)}/config`, values)
      await fetch_render_configs()
    } finally {
      saving_render_config.value = ''
    }
  }

  /** 获取全部带配置项的扩展（代码扩展 + 无代码模板包）；`silent` 用于语言切换等后台刷新 */
  async function fetch_config_items({ silent = false } = {}) {
    if (!silent) config_items_loading.value = true
    try {
      config_items.value = (await http.get('/api/extensions/config-items')) || []
    } finally {
      if (!silent) config_items_loading.value = false
    }
  }

  /** 保存单个扩展的配置项 */
  async function save_config_item(extension_id, values) {
    saving_config_item.value = extension_id
    try {
      await http.patch(`/api/extensions/${encodeURIComponent(extension_id)}/config`, values)
      await fetch_config_items()
    } finally {
      saving_config_item.value = ''
    }
  }

  async function fetch_market(force = false) {
    market_loading.value = true
    try {
      market_items.value = (await http.get('/api/extensions/market', { query: { force } })) || []
    } finally {
      market_loading.value = false
    }
  }

  /**
   * 从市场安装扩展：提交后台任务，进度在任务中心查看。
   *
   * `version` 为 null 表示自动选择兼容当前核心版本的最新历史版本；
   * 传空串则安装最新版本，传具体版本号即切换到该历史版本。
   */
  async function install_market(extension_id, version = null) {
    const task = await http.post('/api/extensions/market/install', { id: extension_id, version })
    await fetch_market()
    return task
  }

  /** 获取扩展的全部可选版本（标记兼容当前核心版本与是否已安装） */
  async function fetch_releases(extension_id) {
    return await http.get(`/api/extensions/market/${encodeURIComponent(extension_id)}/releases`)
  }

  /** 卸载扩展：提交后台任务，进度在任务中心查看 */
  async function uninstall_extension(extension_id) {
    const task = await http.delete(`/api/extensions/${encodeURIComponent(extension_id)}`)
    await fetch_installed()
    return task
  }

  /** 热重载全部扩展（安装/卸载/启停后立即生效，无需重启 Bot）：提交后台任务 */
  async function reload() {
    const task = await http.post('/api/extensions/reload', {})
    return task
  }

  /** 获取图片模式依赖扩展（Html2Pic / Default）的下载情况 */
  async function fetch_image_requirements() {
    image_requirements_loading.value = true
    try {
      image_requirements.value = await http.get('/api/extensions/image-requirements')
      return image_requirements.value
    } finally {
      image_requirements_loading.value = false
    }
  }

  /** 获取 Extension Studio 的下载与运行状态 */
  async function fetch_studio_status() {
    studio_loading.value = true
    try {
      studio_status.value = await http.get('/api/extensions/studio')
      return studio_status.value
    } finally {
      studio_loading.value = false
    }
  }

  /**
   * 下载（如缺失）并启动 Extension Studio。
   *
   * 后端以任务中心任务执行（下载可能较慢），此处等待任务结束，
   * 再返回任务结果中的访问地址（含登录 token）。
   */
  async function launch_studio() {
    studio_launching.value = true
    try {
      const task = await http.post('/api/extensions/studio/launch', {})
      const finished = await useTaskStore().wait_task(task.id)
      await fetch_studio_status()
      if (finished?.status !== 'succeeded') {
        throw new Error(finished?.error || t_global('extensions.studio_launch_failed'))
      }
      return finished.result?.url || ''
    } finally {
      studio_launching.value = false
    }
  }

  /** 停止 Extension Studio */
  async function stop_studio() {
    studio_stopping.value = true
    try {
      await http.post('/api/extensions/studio/stop', {})
      await fetch_studio_status()
    } finally {
      studio_stopping.value = false
    }
  }

  /** 获取 Extension Studio 进程日志 */
  async function fetch_studio_log(tail = 200) {
    studio_log_loading.value = true
    try {
      const data = await http.get('/api/extensions/studio/log', { query: { tail } })
      studio_log.value = data?.content || ''
      return studio_log.value
    } finally {
      studio_log_loading.value = false
    }
  }

  return {
    installed_list,
    loading,
    detail,
    detail_loading,
    config_values,
    config_loading,
    saving_config,
    renderers,
    renderer_loading,
    templates,
    template_loading,
    render_configs,
    render_config_loading,
    saving_render_config,
    config_items,
    config_items_loading,
    saving_config_item,
    market_items,
    market_loading,
    image_requirements,
    image_requirements_loading,
    studio_status,
    studio_loading,
    studio_launching,
    studio_stopping,
    studio_log,
    studio_log_loading,
    fetch_installed,
    fetch_detail,
    fetch_config,
    set_enabled,
    save_config,
    fetch_renderers,
    switch_renderer,
    fetch_templates,
    switch_template,
    fetch_render_configs,
    save_render_config,
    fetch_config_items,
    save_config_item,
    fetch_market,
    install_market,
    fetch_releases,
    uninstall_extension,
    reload,
    fetch_image_requirements,
    fetch_studio_status,
    launch_studio,
    stop_studio,
    fetch_studio_log,
  }
})
