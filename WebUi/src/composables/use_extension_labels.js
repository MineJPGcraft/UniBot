/**
 * 扩展类型 / 状态显示名与徽标变体的统一判定处。
 *
 * 扩展管理页与配置中心的扩展面板都要展示类型徽标与状态徽标，集中在此避免各写
 * 一份映射表。文案经 `useI18n` 的 `t` 求值，随界面语言切换实时更新。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

/** 扩展状态 → Badge 变体 */
const STATE_VARIANTS = {
  loaded: 'success',
  enabled: 'success',
  discovered: 'neutral',
  validated: 'neutral',
  failed: 'danger',
  disabled: 'neutral',
  blocked: 'warning',
}

export function use_extension_labels() {
  const { t } = useI18n()

  /** 扩展类型标识 → 显示名（未知类型原样返回） */
  const type_labels = computed(() => ({
    api: t('extensions.type_api'),
    command: t('extensions.type_command'),
    renderer: t('extensions.type_renderer'),
    template: t('extensions.type_template'),
    resources: t('extensions.type_resources'),
  }))

  /** 扩展状态标识 → 显示名（未知状态原样返回） */
  const state_labels = computed(() => ({
    loaded: t('extensions.state_loaded'),
    enabled: t('extensions.state_enabled'),
    discovered: t('extensions.state_discovered'),
    validated: t('extensions.state_validated'),
    failed: t('extensions.state_failed'),
    disabled: t('extensions.state_disabled'),
    blocked: t('extensions.state_blocked'),
  }))

  function type_label(type) {
    return type_labels.value[type] || type
  }

  function state_label(state) {
    return state_labels.value[state] || state
  }

  function state_variant(state) {
    return STATE_VARIANTS[state] || 'neutral'
  }

  /** 扩展的类型徽标列表：[{ value, label }] */
  function type_badges(extension) {
    return (extension.types || []).map((type) => ({ value: type, label: type_label(type) }))
  }

  return { type_labels, state_labels, type_label, state_label, state_variant, type_badges }
}
