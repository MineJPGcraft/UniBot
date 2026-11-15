/**
 * 配置 Store：Config.toml 配置值、Schema 与 .env 环境变量
 *
 * 后端 Schema 统一为标准 JSON Schema（详见 UniBot/Scripts/Api/Config/Schema.py），
 * 分组信息单独返回；本模块只负责取值/提交，控件语义由 utils/schema_form.js 判定。
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'
import { deep_equal } from '@/utils/equals'
import { get_nested, set_nested } from '@/utils/format'
import {
  each_message_item,
  message_pending,
  message_value as message_value_of,
} from '@/utils/message_tree'

export const useConfigStore = defineStore('config', () => {
  const config_data = ref(null)
  const schema = ref(null) // Config.toml 的 JSON Schema
  const groups = ref([]) // Config.toml 分组 [{ id, name, keys, gated_by? }]
  const draft = ref(null) // 编辑中的副本
  const loading = ref(false)
  const saving = ref(false)

  // .env 环境变量
  const env_values = ref({})
  const env_schema = ref(null) // .env 的 JSON Schema
  const env_groups = ref([])
  const env_draft = ref({})
  const env_loading = ref(false)
  const env_saving = ref(false)

  // 原始文件编辑（Config.toml / .env 源码）
  const raw_config = ref('')
  const raw_env = ref('')
  const raw_config_original = ref('')
  const raw_env_original = ref('')
  const raw_loading = ref(false)
  const raw_saving = ref(false)

  // 消息文本覆盖层（按键命名空间的树 + 逐键草稿）
  const messages_language = ref('zh')
  const messages_tree = ref([])
  const messages_total_count = ref(0)
  const messages_modified_count = ref(0)
  const messages_draft = ref({})
  const messages_loading = ref(false)
  const messages_saving = ref(false)
  /** 草稿相对原配置的变更项：[{ key, label, old_value, new_value }] */
  const changes = computed(() => {
    if (!config_data.value || !draft.value || !schema.value) return []
    const result = []
    for (const [key, field] of Object.entries(schema.value.properties || {})) {
      const old_value = get_nested(config_data.value, key)
      const new_value = get_nested(draft.value, key)
      if (!deep_equal(old_value, new_value)) {
        result.push({ key, label: field.title || key, old_value, new_value })
      }
    }
    return result
  })

  const has_changes = computed(() => changes.value.length > 0)

  /** env 草稿变更项 */
  const env_changes = computed(() => {
    const result = []
    for (const [key, field] of Object.entries(env_schema.value?.properties || {})) {
      const old_value = env_values.value[key]
      const new_value = env_draft.value[key]
      if (!deep_equal(old_value ?? field.default, new_value ?? field.default)) {
        result.push({ key, label: field.title || key, old_value, new_value })
      }
    }
    return result
  })

  const has_env_changes = computed(() => env_changes.value.length > 0)

  /** 原始文件是否有未保存的改动 */
  const has_raw_changes = computed(
    () =>
      raw_config.value !== raw_config_original.value || raw_env.value !== raw_env_original.value,
  )

  /** 未保存的消息改动项：[{ key, value }]（草稿值相对服务端生效值） */
  const messages_changes = computed(() => {
    const result = []
    each_message_item(messages_tree.value, (item) => {
      if (!message_pending(item, messages_draft.value)) return
      result.push({ key: item.key, value: messages_draft.value[item.key] })
    })
    return result
  })

  const has_messages_changes = computed(() => messages_changes.value.length > 0)

  /** 某条消息的生效值：草稿优先，否则用服务端下发的生效值 */
  function message_value(item) {
    return message_value_of(item, messages_draft.value)
  }

  /** 获取 Config.toml 的值与 Schema；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_all({ silent = false } = {}) {
    if (!silent) loading.value = true
    try {
      const [data, schema_data] = await Promise.all([
        http.get('/api/config'),
        http.get('/api/config/schema'),
      ])
      config_data.value = data
      schema.value = schema_data.schema || null
      groups.value = schema_data.groups || []
      draft.value = JSON.parse(JSON.stringify(data))
    } finally {
      if (!silent) loading.value = false
    }
  }

  /**
   * 仅重拉 Config.toml 的 Schema 与分组名（字段标题 / 描述由后端按界面语言下发），
   * 保留 config_data / 用户草稿不变，供语言切换时实时更新表单文案。
   */
  async function fetch_schema() {
    const schema_data = await http.get('/api/config/schema')
    schema.value = schema_data.schema || null
    groups.value = schema_data.groups || []
  }

  /**
   * 获取 .env 的值与 Schema。
   *
   * `silent` 用于语言切换等后台刷新（不触发 loading）；
   * `preserve_draft` 保留未保存的草稿（语言切换场景：重新下发的值与原值一致，
   * 覆盖草稿会丢失用户编辑）。
   */
  async function fetch_env({ silent = false, preserve_draft = false } = {}) {
    if (!silent) env_loading.value = true
    try {
      const data = await http.get('/api/config/env')
      env_values.value = data.values || {}
      env_schema.value = data.schema || null
      env_groups.value = data.groups || []
      if (!preserve_draft) {
        env_draft.value = JSON.parse(JSON.stringify(data.values || {}))
      }
    } finally {
      if (!silent) env_loading.value = false
    }
  }

  function update_field(key, value) {
    draft.value = set_nested(draft.value, key, value)
  }

  function update_env_field(key, value) {
    env_draft.value = { ...env_draft.value, [key]: value }
  }

  function reset_draft() {
    if (config_data.value) {
      draft.value = JSON.parse(JSON.stringify(config_data.value))
    }
  }

  function reset_env_draft() {
    env_draft.value = JSON.parse(JSON.stringify(env_values.value))
  }

  /** 仅提交变更字段（PATCH 深合并） */
  async function save_changes() {
    if (!has_changes.value) return
    saving.value = true
    try {
      let patch = {}
      for (const change of changes.value) {
        patch = set_nested(patch, change.key, change.new_value)
      }
      await http.patch('/api/config', patch)
      await fetch_all()
    } finally {
      saving.value = false
    }
  }

  /** 保存 .env 变更 */
  async function save_env_changes() {
    if (!has_env_changes.value) return
    env_saving.value = true
    try {
      const patch = {}
      for (const change of env_changes.value) {
        patch[change.key] = change.new_value
      }
      await http.patch('/api/config/env', patch)
      await fetch_env()
    } finally {
      env_saving.value = false
    }
  }

  /** 直接写入指定 .env 键值（引导场景用），写入后刷新缓存 */
  async function save_env_fields(fields) {
    await http.patch('/api/config/env', fields)
    await fetch_env()
  }

  /** 获取 Config.toml 与 .env 的原始文本内容 */
  async function fetch_raw() {
    raw_loading.value = true
    try {
      const data = await http.get('/api/config/raw')
      raw_config.value = data.config_toml || ''
      raw_env.value = data.env || ''
      raw_config_original.value = raw_config.value
      raw_env_original.value = raw_env.value
    } finally {
      raw_loading.value = false
    }
  }

  /** 保存原始文件改动（仅提交有变更的文件），返回 { saved_toml, saved_env } */
  async function save_raw() {
    if (!has_raw_changes.value) return { saved_toml: false, saved_env: false }
    raw_saving.value = true
    try {
      const saved_toml = raw_config.value !== raw_config_original.value
      const saved_env = raw_env.value !== raw_env_original.value
      const patch = {}
      if (saved_toml) patch.config_toml = raw_config.value
      if (saved_env) patch.env = raw_env.value
      await http.patch('/api/config/raw', patch)
      raw_config_original.value = raw_config.value
      raw_env_original.value = raw_env.value
      return { saved_toml, saved_env }
    } finally {
      raw_saving.value = false
    }
  }

  /** 获取消息文本分组树（language 由调用方指定，面板内跟随界面语言） */
  async function fetch_messages(language) {
    messages_loading.value = true
    try {
      const data = await http.get(`/api/config/messages?language=${encodeURIComponent(language)}`)
      messages_language.value = data.language || language
      messages_tree.value = data.tree || []
      messages_total_count.value = data.total_count || 0
      messages_modified_count.value = data.modified_count || 0
      messages_draft.value = {}
    } finally {
      messages_loading.value = false
    }
  }

  /** 更新某条消息的草稿值 */
  function update_message(key, value) {
    messages_draft.value = { ...messages_draft.value, [key]: value }
  }

  /** 清空消息草稿 */
  function reset_messages_draft() {
    messages_draft.value = {}
  }

  /** 保存消息改动到覆盖层（提交全部覆盖键，未改动项由后端剔除） */
  async function save_messages() {
    const overrides = {}
    each_message_item(messages_tree.value, (item) => {
      const current = message_value(item)
      if (!deep_equal(current, item.base_value)) {
        overrides[item.key] = current
      }
    })
    messages_saving.value = true
    try {
      const data = await http.patch('/api/config/messages', {
        language: messages_language.value,
        overrides,
      })
      await fetch_messages(messages_language.value)
      return data.modified_count ?? 0
    } finally {
      messages_saving.value = false
    }
  }

  return {
    config_data,
    schema,
    groups,
    draft,
    loading,
    saving,
    changes,
    has_changes,
    fetch_all,
    fetch_schema,
    update_field,
    reset_draft,
    save_changes,
    // env
    env_values,
    env_schema,
    env_groups,
    env_draft,
    env_loading,
    env_saving,
    env_changes,
    has_env_changes,
    fetch_env,
    update_env_field,
    reset_env_draft,
    save_env_changes,
    save_env_fields,
    // 原始文件编辑
    raw_config,
    raw_env,
    raw_config_original,
    raw_env_original,
    raw_loading,
    raw_saving,
    has_raw_changes,
    fetch_raw,
    save_raw,
    // 消息文本
    messages_language,
    messages_tree,
    messages_total_count,
    messages_modified_count,
    messages_draft,
    messages_loading,
    messages_saving,
    messages_changes,
    has_messages_changes,
    message_value,
    fetch_messages,
    update_message,
    reset_messages_draft,
    save_messages,
  }
})
