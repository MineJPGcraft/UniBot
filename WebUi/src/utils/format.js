/**
 * 纯函数工具：格式化时间、时长、字节数等
 */
import { t_global } from '@/i18n'

/** 秒数 → 可读运行时长，如 1天 3小时 12分钟 */
export function format_uptime(seconds) {
  if (!seconds || seconds < 0) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const parts = []
  if (days > 0) parts.push(t_global('users.duration_days', { count: days }))
  if (hours > 0) parts.push(t_global('users.duration_hours', { count: hours }))
  parts.push(t_global('users.duration_minutes', { count: minutes }))
  return parts.join(' ')
}

/** 字节 → 可读大小 */
export function format_bytes(bytes) {
  if (!bytes && bytes !== 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

/** MB → 可读大小（自动换算为 GB 等） */
export function format_mb(megabytes) {
  if (!megabytes && megabytes !== 0) return '—'
  const units = ['MB', 'GB', 'TB']
  let value = megabytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

/** ISO 时间 → 本地可读格式 */
export function format_datetime(iso_string) {
  if (!iso_string) return '—'
  const date = new Date(iso_string)
  if (Number.isNaN(date.getTime())) return iso_string
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** 角色标识 → 中文显示名 */
export function role_label(role) {
  const label_keys = {
    admin: 'users.role_admin',
    operator: 'users.role_operator',
    viewer: 'users.role_viewer',
  }
  return label_keys[role] ? t_global(label_keys[role]) : role
}

/** 日志级别 → 显示色类名 */
export function level_class(level) {
  const map = {
    ERROR: 'text-danger',
    WARNING: 'text-warning',
    SUCCESS: 'text-success',
    INFO: 'text-accent',
    DEBUG: 'text-muted',
  }
  return map[level] || 'text-muted'
}

/** 按路径读取嵌套值，如 get_nested(config, 'image.mode') */
export function get_nested(object, path) {
  return path
    .split('.')
    .reduce((current, key) => (current == null ? undefined : current[key]), object)
}

/** 按路径写入嵌套值（不可变），返回新对象 */
export function set_nested(object, path, value) {
  const keys = path.split('.')
  const result = { ...object }
  let current = result
  for (let index = 0; index < keys.length - 1; index += 1) {
    const key = keys[index]
    current[key] = { ...(current[key] || {}) }
    current = current[key]
  }
  current[keys[keys.length - 1]] = value
  return result
}
