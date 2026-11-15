/**
 * 纯函数工具：Minecraft 服务端类型 → 图标 / 标签映射
 */

import { t_global } from '@/i18n'

/** 服务端类型元信息（label 为语言包键，经 server_type_label 取译文） */
const SERVER_TYPE_META = {
  vanilla: { label: 'servers.type_vanilla', icon: 'lucide:box' },
  spigot: { label: null, icon: 'lucide:package' },
  paper: { label: null, icon: 'lucide:file-text' },
  fabric: { label: null, icon: 'lucide:layers' },
  forge: { label: null, icon: 'lucide:anvil' },
  neoforge: { label: null, icon: 'lucide:hammer' },
}

const DEFAULT_META = { label: 'servers.type_unknown', icon: 'lucide:server' }

/** 根据服务端类型返回 { label, icon }，未知类型回退到默认 */
export function server_type_meta(server_type) {
  const key = (server_type || '').toLowerCase()
  return SERVER_TYPE_META[key] || DEFAULT_META
}

/** 仅返回图标名 */
export function server_type_icon(server_type) {
  return server_type_meta(server_type).icon
}

/** 仅返回标签译文（专有名词直接返回原名，其余取语言包） */
export function server_type_label(server_type) {
  const label = server_type_meta(server_type).label
  return label ? t_global(label) : (server_type || '').toLowerCase()
}
