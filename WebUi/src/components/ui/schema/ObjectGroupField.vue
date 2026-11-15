<script setup>
/**
 * 对象组字段控件：多个子字段纵向排列，每个子字段递归渲染 `SchemaField`。
 *
 * 用于 schema 声明为 object、且子字段不全是 boolean 的场景
 * （全 boolean 的组由 `BooleanGroupField` 渲染为折叠开关列表）。
 */
import { computed } from 'vue'
import { is_plain_object } from '@/utils/schema_form'
import SchemaField from '../SchemaField.vue'

const props = defineProps({
  schema: { type: Object, required: true },
  modelValue: { type: Object, default: () => ({}) },
  rootSchema: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const entries = computed(() => Object.entries(props.schema.properties || {}))

const current = computed(() => (is_plain_object(props.modelValue) ? props.modelValue : {}))

function update_field(name, value) {
  emit('update:modelValue', { ...current.value, [name]: value })
}
</script>

<template>
  <div class="field-object-group">
    <div v-for="[name, child] in entries" :key="name" class="field-subfield">
      <div class="field-subfield-label">{{ child.title || name }}</div>
      <p v-if="child.description" class="field-subfield-desc">{{ child.description }}</p>
      <SchemaField
        :schema="child"
        :field-key="name"
        :root-schema="rootSchema"
        :model-value="current[name]"
        :disabled="disabled"
        @update:model-value="(value) => update_field(name, value)"
      />
    </div>
  </div>
</template>

<style scoped>
.field-object-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}

.field-subfield {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.field-subfield-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
}

.field-subfield-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

.field-subfield :deep(.ui-input),
.field-subfield :deep(.ui-textarea),
.field-subfield :deep(.ui-select-trigger) {
  width: 100%;
}
</style>
