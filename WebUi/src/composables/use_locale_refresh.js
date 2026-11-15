/**
 * 界面语言切换后的数据刷新。
 *
 * 后端按每请求的 `Accept-Language` 下发界面文案（配置 schema 的字段标题 / 描述 /
 * 分组名、适配器目录、扩展与插件列表等）；已经拉取到前端的数据不会随界面语言
 * 自动变化，因此在语言切换后统一重拉「已加载过」的语言相关数据。未加载过的数据
 * 保持惰性，等页面挂载时按新语言拉取即可。
 *
 * 约定：
 * - 由 AppLayout 调用一次（应用生命周期单例），watch 挂在独立 effectScope 上；
 * - 重拉一律传 `silent`，不切换各 store 的 loading 标志：避免页面闪 loading、
 *   表单被卸载导致未保存的草稿丢失；
 * - 刷新任务串行执行，连续切换语言时以最后一次为准，单个失败不影响其余刷新；
 * - 未登录时不刷新（登录页无已加载数据，避免 401 触发跳转与无效请求）。
 */
import { effectScope, watch } from 'vue'
import { current_locale } from '@/i18n'
import { is_authenticated } from '@/utils/http'
import { useAdapterStore } from '@/stores/adapter'
import { useConfigStore } from '@/stores/config'
import { useExtensionStore } from '@/stores/extension'
import { usePluginStore } from '@/stores/plugin'

let started = false
/** 刷新串行链：避免连续切换语言时新旧语言的响应相互覆盖 */
let refresh_chain = Promise.resolve()

/** 数据是否已加载过（列表以非空判断；未加载与空列表都不需要刷新——没有可更新的文案） */
function has_loaded(value) {
  return Array.isArray(value) ? value.length > 0 : Boolean(value)
}

/** 重拉全部已加载的语言相关数据 */
async function refresh_language_data() {
  if (!is_authenticated()) return

  const config_store = useConfigStore()
  const adapter_store = useAdapterStore()
  const extension_store = useExtensionStore()
  const plugin_store = usePluginStore()

  const tasks = []

  // 配置中心：字段标题 / 描述 / 分组名与 .env schema 由后端按界面语言下发
  if (has_loaded(config_store.schema)) {
    tasks.push(() => config_store.fetch_schema())
  }
  if (has_loaded(config_store.env_schema)) {
    tasks.push(() => config_store.fetch_env({ preserve_draft: true, silent: true }))
  }
  // 适配器目录：名称 / 描述 / 平台标签由后端按界面语言下发
  if (has_loaded(adapter_store.catalog) || has_loaded(adapter_store.registered_list)) {
    tasks.push(() => adapter_store.fetch_all({ silent: true }))
  }
  // 扩展列表与配置（名称、描述、schema 文案）
  if (has_loaded(extension_store.installed_list)) {
    tasks.push(() => extension_store.fetch_installed({ silent: true }))
  }
  if (has_loaded(extension_store.renderers)) {
    tasks.push(() => extension_store.fetch_renderers({ silent: true }))
  }
  if (has_loaded(extension_store.templates)) {
    tasks.push(() => extension_store.fetch_templates({ silent: true }))
  }
  if (has_loaded(extension_store.render_configs)) {
    tasks.push(() => extension_store.fetch_render_configs({ silent: true }))
  }
  if (has_loaded(extension_store.config_items)) {
    tasks.push(() => extension_store.fetch_config_items({ silent: true }))
  }
  // 扩展配置弹窗已打开时，同步刷新其中的详情与配置（标签实时切换语言）
  const active_extension_id = extension_store.detail?.id
  if (active_extension_id) {
    tasks.push(() => extension_store.fetch_detail(active_extension_id, { silent: true }))
    tasks.push(() => extension_store.fetch_config(active_extension_id, { silent: true }))
  }
  // 插件列表（内置插件名称 / 描述为延迟求值译文）
  if (has_loaded(plugin_store.installed_list)) {
    tasks.push(() => plugin_store.fetch_installed({ silent: true }))
  }

  await Promise.all(
    tasks.map((task) =>
      Promise.resolve()
        .then(task)
        .catch((error) => {
          console.warn('refresh language-dependent data failed', error)
        }),
    ),
  )
}

/** 启动界面语言监听（幂等；由 AppLayout 调用） */
export function use_locale_refresh() {
  if (started) return
  started = true
  // detached scope：watch 需跨路由常驻（登录 / 登出时 AppLayout 会卸载重建）
  const scope = effectScope(true)
  scope.run(() => {
    watch(
      () => current_locale(),
      () => {
        refresh_chain = refresh_chain.then(refresh_language_data, refresh_language_data)
      },
    )
  })
}
