/**
 * i18n 入口：基于 vue-i18n 的轻量封装。
 * - 语言仅 zh / en 两种，持久化在 localStorage，默认中文
 * - 与机器人消息语言（Config.toml 的 language）完全独立
 * - 各界面文案为 messages/ 下的 JSON 语言包，键名与文件名同名作为顶层命名空间
 */
import { createI18n } from 'vue-i18n'

import common from './messages/common.json'
import nav from './messages/nav.json'
import layout from './messages/layout.json'
import login from './messages/login.json'
import dashboard from './messages/dashboard.json'
import config_view from './messages/config_view.json'
import extensions from './messages/extensions.json'
import servers from './messages/servers.json'
import players from './messages/players.json'
import adapters from './messages/adapters.json'
import plugins from './messages/plugins.json'
import users from './messages/users.json'
import settings from './messages/settings.json'
import setup from './messages/setup.json'
import statistics from './messages/statistics.json'
import logs from './messages/logs.json'
import task_center from './messages/task_center.json'
import ui from './messages/ui.json'

/** 支持的语言清单（切换器渲染用） */
export const LOCALES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
]

export const LOCALE_STORAGE_KEY = 'unibot_locale'

const MESSAGE_MODULES = {
  common,
  nav,
  layout,
  login,
  dashboard,
  config_view,
  extensions,
  servers,
  players,
  adapters,
  plugins,
  users,
  settings,
  setup,
  statistics,
  logs,
  task_center,
  ui,
}

function initial_locale() {
  return localStorage.getItem(LOCALE_STORAGE_KEY) === 'en' ? 'en' : 'zh'
}

const i18n = createI18n({
  legacy: false,
  locale: initial_locale(),
  fallbackLocale: 'zh',
  missingWarn: false,
  fallbackWarn: false,
  messages: { zh: {}, en: {} },
})

for (const [namespace, pack] of Object.entries(MESSAGE_MODULES)) {
  i18n.global.mergeLocaleMessage('zh', { [namespace]: pack.zh })
  i18n.global.mergeLocaleMessage('en', { [namespace]: pack.en })
}

/** 当前语言 */
export function current_locale() {
  return i18n.global.locale.value
}

/** 语言对应的 <html lang> 声明（zh 用 zh-CN，与 index.html 默认一致） */
function html_lang(locale) {
  return locale === 'en' ? 'en' : 'zh-CN'
}

/** 切换语言并持久化（组件内响应式生效） */
export function set_locale(locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  document.documentElement.lang = html_lang(locale)
}

/** 组件外取译文（http.js / composable 等非组件上下文使用） */
export function t_global(key, params) {
  return params ? i18n.global.t(key, params) : i18n.global.t(key)
}

export default i18n
