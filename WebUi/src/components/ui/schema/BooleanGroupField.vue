<script setup>
/**
 * 布尔组字段控件：一组开关，收在折叠面板里。
 *
 * 面板标题来自字段 schema 的 `title`（缺失时用字段名），右侧徽标显示
 * 「已开启数 / 总数」，方便一眼看出组内开关状态。
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { is_plain_object } from '@/utils/schema_form'
import Collapsible from '../Collapsible.vue'
import Switch from '../Switch.vue'

const props = defineProps({
  /** 字段定义（`properties` 全为 boolean） */
  schema: { type: Object, required: true },
  /** 字段名（schema 无 title 时的兜底标题） */
  fieldKey: { type: String, default: '' },
  modelValue: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const group_open = ref(false)

const entries = computed(() => Object.entries(props.schema.properties || {}))

const current = computed(() => (is_plain_object(props.modelValue) ? props.modelValue : {}))

const opened_count = computed(
  () => entries.value.filter(([name]) => Boolean(current.value[name])).length,
)

function update_field(name, value) {
  emit('update:modelValue', { ...current.value, [name]: value })
}
</script>

<template>
  <Collapsible v-model="group_open" :disabled="disabled">
    <template #trigger>
      <span class="field-collapse-title">{{ schema.title || fieldKey }}</span>
      <span class="field-collapse-count">
        {{
          t('ui.form_editor_booleans_enabled_count', {
            opened: opened_count,
            total: entries.length,
          })
        }}
      </span>
    </template>
    <template #content>
      <div class="field-collapse-list">
        <label
          v-for="[name, child] in entries"
          :key="name"
          class="field-boolean"
          :title="child.description"
        >
          <Switch
            :model-value="Boolean(current[name])"
            :disabled="disabled"
            @update:model-value="(value) => update_field(name, value)"
          />
          <span class="field-boolean-text">{{ child.title || name }}</span>
        </label>
      </div>
    </template>
  </Collapsible>
</template>

<style scoped>
.field-collapse-title {
  flex: 1;
  font-weight: 500;
}

.field-collapse-count {
  flex: 0 0 auto;
  padding: 1px var(--space-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--text-muted);
}

.field-collapse-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-height: 220px;
  overflow-y: auto;
  padding: var(--space-1);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.field-boolean {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color var(--transition);
}

.field-boolean:hover {
  background: var(--surface-soft);
}

.field-boolean-text {
  font-size: var(--text-sm);
  color: var(--text);
}
</style>
