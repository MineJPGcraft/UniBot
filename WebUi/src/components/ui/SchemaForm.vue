<script setup>
/**
 * 通用 schema 表单（字段行布局）。
 *
 * 按「左侧标题 / 描述 + 右侧控件」的行布局渲染一组字段，控件由 SchemaField 提供。
 * 单字段行内联使用（ConfigView），整表由父组件经 ref 调用 confirm_save / reset_draft
 * 或监听 change 事件自行渲染操作栏。
 *
 * `values` 为当前值快照，草稿由内部维护：仅在 schema 或 values 首次就绪时重建，
 * 避免父组件刷新 values 时覆盖用户未保存的编辑。
 *
 * schema 变化（如切换界面语言后后端重下发的标题 / 描述）默认会重建草稿；
 * 传入 `keepDraftOnSchemaChange` 时仅更新字段文案，保留用户未保存的编辑。
 */
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { create_change_detector } from '@/utils/equals'
import Button from './Button.vue'
import Spinner from './Spinner.vue'
import EmptyState from './EmptyState.vue'
import SchemaField from './SchemaField.vue'
import {
  clone,
  default_value,
  field_layout,
  normalize_value,
  schema_fields,
  serialize_value,
} from '@/utils/schema_form'

const props = defineProps({
  /** 根 JSON Schema */
  schema: { type: Object, default: null },
  /** 当前值 */
  values: { type: Object, default: () => ({}) },
  /** 仅渲染这些字段（顺序即显示顺序）；省略则用 schema 声明顺序 */
  fields: { type: Array, default: null },
  /** 是否字段名使用点号路径取值（Config.toml 的 `image.mode` 形态） */
  nested: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  /** 展示内置操作栏（撤销 / 保存） */
  showActions: { type: Boolean, default: true },
  /** 高亮这些字段（如门控锁定） */
  lockedKeys: { type: Array, default: () => [] },
  /**
   * schema 变化时保留草稿（仅更新标题 / 描述等文案）。
   * 用于语言切换后重拉 schema 的场景，避免丢失未保存的编辑。
   */
  keepDraftOnSchemaChange: { type: Boolean, default: false },
})

const emit = defineEmits(['save', 'change', 'update'])

const { t } = useI18n()

const draft = reactive({})

/** 字段级变更判定器：按「原值 / 草稿值引用」缓存，避免每次渲染全表深比较 */
const is_field_changed = create_change_detector()

const field_list = computed(() => schema_fields(props.schema, props.fields))

function read_value(source, key) {
  if (!props.nested) return source?.[key]
  return key
    .split('.')
    .reduce((node, segment) => (node == null ? undefined : node[segment]), source)
}

/** 初始化**尚未编辑**的字段（已有草稿值保留，切换分组不丢改动） */
function initialize_draft() {
  for (const field of field_list.value) {
    if (field.key in draft) continue
    const current = read_value(props.values, field.key)
    draft[field.key] =
      current === undefined ? default_value(field.schema, field.key) : clone(current)
  }
}

/** 丢弃全部草稿改动，回到原始值 */
function reset_draft() {
  for (const key of Object.keys(draft)) delete draft[key]
  initialize_draft()
}

watch(
  () => props.schema,
  () => {
    if (!props.schema) return
    if (props.keepDraftOnSchemaChange) {
      // 仅更新字段文案（标题 / 描述），保留未保存草稿
      initialize_draft()
      return
    }
    reset_draft()
  },
  { immediate: true },
)

// 渲染字段集变化时补齐新字段（保留已编辑字段）
watch(() => props.fields, initialize_draft)

// values 刷新（保存后重新拉取）且当前无未保存改动时整体重建（草稿保护）
watch(
  () => props.values,
  () => {
    if (!props.schema || has_changes.value) return
    reset_draft()
  },
)

/** 已改动字段 key 集合（首次比较后按「原值 / 草稿值引用」缓存，输入时只重算改动字段） */
const changed_keys = computed(() => {
  const changed = new Set()
  for (const field of field_list.value) {
    const current = draft[field.key]
    const original = read_value(props.values, field.key)
    const normalized_current = normalize_value(field.schema, field.key, current)
    const normalized_original = normalize_value(field.schema, field.key, original)
    if (is_field_changed(field.key, normalized_original, normalized_current)) {
      changed.add(field.key)
    }
  }
  return changed
})

const has_changes = computed(() => changed_keys.value.size > 0)

watch(
  () => changed_keys.value.size,
  (count) => emit('change', count),
  { immediate: true },
)

/** 字段取值变更：写入草稿并向上同步该字段（受控父组件据此更新自身草稿） */
function on_field_update(key, value) {
  draft[key] = value
  emit('update', { key, value })
}

/** 校验并提交：对象数组元素按子 schema 归一化 */
function confirm_save() {
  const payload = {}
  for (const field of field_list.value) {
    const value = draft[field.key]
    payload[field.key] = serialize_value(field.schema, field.key, value)
  }
  emit('save', payload)
}

/** 字段行布局修饰类：沿用 `field_layout` 档位，`inline` 无修饰类 */
function row_layout_class(field) {
  const layout = field_layout(field.schema, field.key)
  return layout === 'inline' ? '' : `field-row--${layout}`
}

defineExpose({ confirm_save, reset_draft, has_changes })
</script>

<template>
  <div v-if="loading" class="form-loading"><Spinner :size="18" /> {{ t('ui.form_loading') }}</div>
  <EmptyState
    v-else-if="!schema || field_list.length === 0"
    icon="lucide:file-cog"
    :title="t('ui.form_empty')"
  />
  <div v-else class="schema-form">
    <div v-if="showActions" class="form-actions">
      <div class="form-actions-left">
        <slot name="actions-left" />
      </div>
      <Button variant="ghost" :disabled="!has_changes" @click="reset_draft">
        {{ t('ui.form_revert') }}
      </Button>
      <Button
        variant="primary"
        :loading="saving"
        :disabled="disabled || !has_changes"
        @click="confirm_save"
      >
        <Icon icon="lucide:save" width="15" />
        {{ t('ui.form_save') }}
        <span v-if="has_changes" class="change-count">{{ changed_keys.size }}</span>
      </Button>
    </div>
    <div
      v-for="field in field_list"
      :key="field.key"
      class="field-row"
      :class="[
        row_layout_class(field),
        {
          'field-row--changed': changed_keys.has(field.key),
          'field-locked': lockedKeys.includes(field.key),
        },
      ]"
    >
      <div class="field-meta">
        <label class="field-label">
          {{ field.title }}
          <span v-if="!nested" class="mono field-key">{{ field.key }}</span>
        </label>
        <p v-if="field.description" class="field-desc">{{ field.description }}</p>
      </div>
      <div class="field-control">
        <SchemaField
          :schema="field.schema"
          :field-key="field.key"
          :root-schema="schema"
          :model-value="draft[field.key]"
          :disabled="disabled"
          @update:model-value="(value) => on_field_update(field.key, value)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.schema-form {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
}

.form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.form-actions-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-right: auto;
}

.change-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.25);
  font-size: var(--text-xs);
}

/* 字段行：左描述 / 右控件 */
.field-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-4) 0;
}

.field-row + .field-row {
  border-top: 1px solid var(--border);
}

.field-row--changed {
  margin: 0 calc(-1 * var(--space-4));
  padding-right: var(--space-4);
  padding-left: var(--space-4);
  border-radius: var(--radius);
  background: linear-gradient(to right, var(--warning-soft), transparent 60%);
}

/* 门控开关行：提升到父级锁定遮罩之上，保持可交互 */
.field-locked {
  position: relative;
  z-index: 2;
}

/* 整行纵向排布：通栏（多行文本 / 键值映射 / 折叠组）与列表类窄屏共用 */
.field-row--wide,
.field-row--aside {
  flex-direction: column;
  align-items: stretch;
  gap: var(--space-3);
}

.field-row--wide .field-control {
  flex: 1 1 auto;
  justify-content: flex-start;
  width: 100%;
}

/* 列表类（对象数组 / 字符列表 / 平台列表）：限制宽度并靠右对齐，避免通栏后被拉散 */
.field-row--aside .field-control {
  flex: 1 1 auto;
  justify-content: flex-end;
  width: 100%;
}

.field-row--aside .field-control > :deep(.field-object-list),
.field-row--aside .field-control > :deep(.field-list-editor) {
  width: 100%;
  max-width: 620px;
  margin-inline-start: auto;
}

.field-meta {
  flex: 1;
  min-width: 0;
}

.field-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.field-key {
  padding: 0 var(--space-1);
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface-sunken);
  font-size: 11px;
  color: var(--text-muted);
}

.field-desc {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

.field-control {
  display: flex;
  flex: 0 0 40%;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  width: 40%;
  min-width: 0;
}

/* 单选控件填满右侧栏；开关等内联控件保持自身宽度。
   Select 等控件内部元素需 :deep() 才可命中（同 ConfigView 先例） */
.field-control > :deep(.ui-input),
.field-control > :deep(.ui-textarea),
.field-control > :deep(.ui-select-trigger),
.field-control > :deep(.field-color) {
  width: 100%;
}

.field-control > :deep(.ui-select-trigger) {
  justify-content: space-between;
}

/* 宽屏：列表回到右栏独立成块并靠右显示 */
@media (min-width: 1100px) {
  .field-row--aside {
    flex-direction: row;
    align-items: flex-start;
    gap: var(--space-6);
  }

  .field-row--aside .field-meta {
    flex: 1 1 auto;
  }

  .field-row--aside .field-control {
    flex: 0 0 58%;
    justify-content: flex-end;
    width: 58%;
  }
}

@media (max-width: 900px) {
  .field-row {
    flex-direction: column;
    gap: var(--space-3);
  }

  .field-control {
    flex: 1 1 auto;
    justify-content: flex-start;
    width: 100%;
  }
}
</style>
