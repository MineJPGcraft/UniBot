<script setup>
/**
 * 通用 schema 字段控件（递归分发器）。
 *
 * 按 `utils/schema_form.js` 判定的控件语义分发给具体控件组件
 * （`schema/` 子目录），本文件只负责：
 * - `$ref` / `anyOf` 解引用与 `field_kind` 判定；
 * - 把界面取值经 `serialize_value` 归一化后上抛（值语义与 schema 同构）；
 * - 标量控件（开关 / 下拉 / 颜色 / 数字 / 文本 / 多行文本）的内联渲染。
 *
 * 复杂控件（列表 / 对象数组 / 键值映射 / 布尔组 / 对象组）在 `schema/` 下独立成组件，
 * 递归时统一回落到本分发器。不含标签 / 描述行布局（由 SchemaForm 负责）。
 * Config.toml / .env / 扩展配置三处表单共用本组件。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  color_value,
  dereference,
  effective_schema,
  field_kind,
  number_step,
  select_options,
  serialize_value,
} from '@/utils/schema_form'
import Input from './Input.vue'
import Textarea from './Textarea.vue'
import Switch from './Switch.vue'
import Select from './Select.vue'
import StringListField from './schema/StringListField.vue'
import PlatformListField from './schema/PlatformListField.vue'
import ObjectListField from './schema/ObjectListField.vue'
import KeyValueField from './schema/KeyValueField.vue'
import BooleanGroupField from './schema/BooleanGroupField.vue'
import ObjectGroupField from './schema/ObjectGroupField.vue'

const props = defineProps({
  /** 字段 schema（可为 $ref，会按 rootSchema 解引用） */
  schema: { type: Object, required: true },
  /** 字段名（用于密钥启发式与默认值） */
  fieldKey: { type: String, default: '' },
  /** 所属根 schema（解析 $ref 用） */
  rootSchema: { type: Object, default: null },
  modelValue: { type: [String, Number, Boolean, Array, Object], default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

/** 解引用并解包 anyOf 后的字段定义 */
const resolved = computed(() => {
  const target = dereference(props.rootSchema, props.schema) || props.schema
  return effective_schema(target) || target
})

const kind = computed(() => field_kind(resolved.value, props.fieldKey))

function update(value) {
  emit('update:modelValue', serialize_value(resolved.value, props.fieldKey, value))
}
</script>

<template>
  <Switch
    v-if="kind === 'boolean'"
    :model-value="Boolean(modelValue)"
    :disabled="disabled"
    @update:model-value="update"
  />
  <Select
    v-else-if="kind === 'select'"
    :model-value="modelValue ?? ''"
    :options="select_options(resolved)"
    :disabled="disabled"
    @update:model-value="update"
  />
  <div v-else-if="kind === 'color'" class="field-color">
    <input
      type="color"
      class="field-color-picker"
      :value="color_value(modelValue)"
      :disabled="disabled"
      @input="update($event.target.value)"
    />
    <Input
      :model-value="modelValue ?? ''"
      :placeholder="t('ui.form_color_placeholder')"
      :disabled="disabled"
      @update:model-value="update"
    />
  </div>
  <Input
    v-else-if="kind === 'number'"
    :model-value="modelValue ?? ''"
    type="number"
    :min="resolved.minimum"
    :max="resolved.maximum"
    :step="number_step(resolved)"
    :disabled="disabled"
    @update:model-value="update"
  />
  <Input
    v-else-if="kind === 'password'"
    :model-value="modelValue ?? ''"
    type="password"
    :placeholder="t('ui.form_secret_placeholder')"
    :disabled="disabled"
    @update:model-value="update"
  />
  <Textarea
    v-else-if="kind === 'textarea'"
    :model-value="modelValue ?? ''"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 普通单行文本（string 的默认形态） -->
  <Input
    v-else-if="kind === 'text'"
    :model-value="modelValue ?? ''"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 字符串列表 -->
  <StringListField
    v-else-if="kind === 'string_list'"
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 平台列表 -->
  <PlatformListField
    v-else-if="kind === 'platform_list'"
    :model-value="modelValue"
    :options="resolved['x-options'] || []"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 对象数组（卡片列表） -->
  <ObjectListField
    v-else-if="kind === 'object_list'"
    :schema="resolved"
    :root-schema="rootSchema"
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 布尔组（折叠面板内的一组开关） -->
  <BooleanGroupField
    v-else-if="kind === 'boolean_group'"
    :schema="resolved"
    :field-key="fieldKey"
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 对象组（多种子类型的对象，逐个子字段渲染） -->
  <ObjectGroupField
    v-else-if="kind === 'object_group'"
    :schema="resolved"
    :root-schema="rootSchema"
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="update"
  />

  <!-- 键值对 -->
  <KeyValueField
    v-else-if="kind === 'key_value'"
    :schema="resolved"
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="update"
  />

  <div v-else class="field-unsupported">{{ t('ui.form_unsupported_type') }}</div>
</template>

<script>
// 递归自引用：字段控件需渲染嵌套对象
export default { name: 'SchemaField' }
</script>

<style scoped>
/* 颜色选择器 */
.field-color {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
}

.field-color :deep(.ui-input) {
  flex: 1;
}

.field-color-picker {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  padding: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: border-color var(--transition);
}

.field-color-picker::-webkit-color-swatch-wrapper {
  padding: 0;
}

.field-color-picker::-webkit-color-swatch {
  border: none;
  border-radius: 3px;
}

.field-color-picker:hover:not(:disabled) {
  border-color: var(--border-strong);
}

.field-color-picker:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-unsupported {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
