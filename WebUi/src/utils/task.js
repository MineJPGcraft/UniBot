/**
 * 纯函数工具：任务中心的状态文案、图标与标题渲染
 *
 * 任务标题与阶段说明由后端下发「消息键 + 参数」，此处只做映射与翻译，
 * 保证切换界面语言后历史任务文案也跟着变。
 */
import { t_global } from '@/i18n'

/** 任务状态 → Badge 变体 */
export const STATUS_VARIANTS = {
  pending: 'neutral',
  running: 'accent',
  succeeded: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

/** 未结束的状态（可取消、需继续轮询） */
export const ACTIVE_STATUSES = new Set(['pending', 'running'])

/** 任务类型 → 图标（key 与后端 `Scripts/Constants.py` 的 `TaskKind` 枚举成员值一致） */
const KIND_ICONS = {
  dependency_sync: 'lucide:package-search',
  extension_install: 'lucide:puzzle',
  extension_uninstall: 'lucide:package-minus',
  extension_reload: 'lucide:refresh-cw',
  adapter_install: 'lucide:cable',
  adapter_uninstall: 'lucide:cable',
  studio_launch: 'lucide:app-window',
  plugin_install: 'lucide:plug',
  plugin_upgrade: 'lucide:arrow-up-circle',
  plugin_uninstall: 'lucide:plug-zap',
  bot_update: 'lucide:download',
}

/** 标题参数名 → 标题模板键（按任务类型前缀选择） */
const TITLE_KEYS = [
  { prefix: 'plugin', key: 'task_center.title_plugin' },
  { prefix: 'adapter', key: 'task_center.title_adapter' },
]

/** 状态码 → Badge 变体，未知状态回退中性色 */
export function status_variant(status) {
  return STATUS_VARIANTS[status] || 'neutral'
}

/** 任务是否仍在排队或运行中 */
export function is_active(task) {
  return ACTIVE_STATUSES.has(task?.status)
}

/** 任务类型图标，未知类型回退旋转图标 */
export function kind_icon(kind) {
  return KIND_ICONS[kind] || 'lucide:loader'
}

/** 任务类型名（语言包缺失时回退「后台任务」） */
export function kind_label(kind) {
  const key = `task_center.kind_${kind}`
  const label = t_global(key)
  return label === key ? t_global('task_center.kind_unknown') : label
}

/** 状态名 */
export function status_label(status) {
  const key = `task_center.status_${status}`
  const label = t_global(key)
  return label === key ? status : label
}

/** 任务标题：类型名 + 关键参数（扩展 / 适配器 / 插件名或依赖包名） */
export function task_title(task) {
  const params = task.title_params || {}
  if (params.name) {
    const matched = TITLE_KEYS.find((item) => task.kind.startsWith(item.prefix))
    const key = matched ? matched.key : 'task_center.title_extension'
    return `${kind_label(task.kind)} · ${t_global(key, { name: params.name })}`
  }
  if (params.packages) {
    return `${kind_label(task.kind)} · ${t_global('task_center.title_package', { packages: params.packages })}`
  }
  return kind_label(task.kind)
}

/** 阶段说明（message_key + message_params，缺省回退到状态名） */
export function task_message(task) {
  if (!task.message_key) return status_label(task.status)
  const translated = t_global(task.message_key, task.message_params || {})
  return translated === task.message_key ? status_label(task.status) : translated
}

/** 运行时长（秒），未结束的任务按当前时刻实时计算 */
export function task_elapsed_seconds(task) {
  const started = task.started_at || task.created_at
  if (!started) return 0
  const finished = task.finished_at || Date.now() / 1000
  return Math.max(0, Math.round(finished - started))
}

/** 运行时长 → 紧凑文本，如 12s / 3m 5s / 1h 20m */
export function format_elapsed(seconds) {
  if (!seconds) return ''
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}
