/**
 * 语言包编译校验：逐条用 vue-i18n 消息编译器验证 messages/*.json，
 * 捕获非法占位符 / 字面量转义（如 {"@"} 应为 {'@'}）等语法错误。
 * 用法：bun run check:locales
 */
import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

// 借助含消息编译器的完整构建（esm-bundler 不导出 compile）
const vi18n = await import(
  join(
    dirname(fileURLToPath(import.meta.url)),
    '../node_modules/vue-i18n/dist/vue-i18n.esm-browser.js',
  )
)

const MESSAGES_DIR = join(dirname(fileURLToPath(import.meta.url)), '../src/i18n/messages')
const LOCALES = ['zh', 'en']

let total = 0
let errors = 0

for (const file of readdirSync(MESSAGES_DIR).filter((name) => name.endsWith('.json'))) {
  const pack = JSON.parse(readFileSync(join(MESSAGES_DIR, file), 'utf8'))
  for (const locale of LOCALES) {
    const flat = {}
    const walk = (node, prefix) => {
      for (const [key, value] of Object.entries(node)) {
        if (typeof value === 'object') walk(value, `${prefix}${key}.`)
        else flat[`${prefix}${key}`] = value
      }
    }
    walk(pack[locale] ?? {}, '')
    for (const [key, value] of Object.entries(flat)) {
      total++
      if (typeof value !== 'string') continue
      let captured = null
      const original_error = console.error
      console.error = (...args) => {
        if (!captured) captured = args.join(' ')
      }
      try {
        // 独立实例逐条注册并触发编译，避免跨键缓存干扰
        const i18n = vi18n.createI18n({
          legacy: false,
          locale,
          fallbackLocale: locale,
          messages: { [locale]: {} },
        })
        i18n.global.setLocaleMessage(locale, { [key]: value })
        i18n.global.t(key)
      } catch (error) {
        captured = error.message
      } finally {
        console.error = original_error
      }
      if (captured && /compilation error|Invalid token/i.test(captured)) {
        errors++
        console.log(`✗ ${file} ${locale} ${key}: ${value}\n  ${captured.split('\n')[0]}`)
      }
    }
  }
}

console.log(`checked ${total} messages, ${errors} compilation errors`)
if (errors > 0) process.exit(1)
