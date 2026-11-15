<script setup>
/**
 * 键值映射字段控件（`additionalProperties`）。
 *
 * 每行是 `键 → 值`：值为数组形态（`additionalProperties.type === 'array'`）时，
 * 该行右侧渲染为可增删的字符串列表（如「命令 → 别名列表」）。
 *
 * 键与行内列表各用独立的稳定 key 簿记，删除中间行 / 中间项时输入框状态不串位。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_list_keys } from '@/composables/use_list_keys'
import { clone, is_plain_object } from '@/utils/schema_form'
import Input from '../Input.vue'
import Button from '../Button.vue'

const props = defineProps({
  /** 字段定义（用 `additionalProperties` 描述值类型） */
  schema: { type: Object, required: true },
  modelValue: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

/** 映射行的稳定 key 簿记 */
const row_keys = use_list_keys()
/** 行内列表的稳定 key 簿记（键为所在行的稳定 key） */
const list_keys_map = new Map()

function list_keys_of(row_key) {
  if (!list_keys_map.has(row_key)) list_keys_map.set(row_key, use_list_keys())
  return list_keys_map.get(row_key)
}

/** 映射行内列表项的稳定 key（行下标 → 列表项 key） */
function list_key_for(row_index, item_index) {
  return list_keys_of(row_keys.key_for(row_index)).key_for(item_index)
}

const entries = computed(() => {
  const value = props.modelValue
  if (!is_plain_object(value)) return []
  return Object.entries(value)
})

const value_schema = computed(() => props.schema.additionalProperties || { type: 'string' })

const is_list_value = computed(() => value_schema.value.type === 'array')

function commit(next_entries) {
  emit('update:modelValue', Object.fromEntries(next_entries))
}

function update_key(index, key) {
  const next = clone(entries.value)
  next[index][0] = key
  commit(next)
}

function update_value(index, value) {
  const next = clone(entries.value)
  next[index][1] = value
  commit(next)
}

function add_entry() {
  const next = clone(entries.value)
  next.push(['', is_list_value.value ? [] : ''])
  commit(next)
}

function remove_entry(index) {
  const next = clone(entries.value)
  next.splice(index, 1)
  // 同步移除该行的稳定 key 与行内列表簿记，避免后续行继承已删除行的状态
  const removed_key = row_keys.key_for(index)
  row_keys.remove(index)
  list_keys_map.delete(removed_key)
  commit(next)
}

function update_list_item(index, item_index, value) {
  const next = clone(entries.value)
  const list = Array.isArray(next[index][1]) ? next[index][1] : []
  list[item_index] = value
  next[index][1] = list
  commit(next)
}

function add_list_item(index) {
  const next = clone(entries.value)
  const list = Array.isArray(next[index][1]) ? next[index][1] : []
  list.push('')
  next[index][1] = list
  commit(next)
}

function remove_list_item(index, item_index) {
  const next = clone(entries.value)
  const list = Array.isArray(next[index][1]) ? next[index][1] : []
  list.splice(item_index, 1)
  next[index][1] = list
  list_keys_of(row_keys.key_for(index)).remove(item_index)
  commit(next)
}
</script>

<template>
  <div class="field-map">
    <div v-for="(entry, index) in entries" :key="row_keys.key_for(index)" class="field-map-row">
      <Input
        :model-value="entry[0]"
        :placeholder="schema['x-key-label']"
        class="field-map-key"
        :disabled="disabled"
        @update:model-value="(value) => update_key(index, value)"
      />
      <span class="field-map-arrow">→</span>
      <div v-if="is_list_value" class="field-map-list">
        <div
          v-for="(item, item_index) in entry[1] || []"
          :key="list_key_for(index, item_index)"
          class="field-map-list-row"
        >
          <Input
            :model-value="item"
            :placeholder="schema['x-value-placeholder']"
            :disabled="disabled"
            @update:model-value="(value) => update_list_item(index, item_index, value)"
          />
          <Button
            variant="ghost"
            size="sm"
            icon-only
            :disabled="disabled"
            @click="remove_list_item(index, item_index)"
          >
            <Icon icon="lucide:x" width="14" />
          </Button>
        </div>
        <Button
          variant="secondary"
          size="xs"
          class="field-add"
          :disabled="disabled"
          @click="add_list_item(index)"
        >
          <Icon icon="lucide:plus" width="13" />
          {{ t('ui.form_editor_add_address') }}
        </Button>
      </div>
      <Input
        v-else
        :model-value="entry[1]"
        :placeholder="schema['x-value-placeholder']"
        class="field-map-value"
        :disabled="disabled"
        @update:model-value="(value) => update_value(index, value)"
      />
      <Button variant="ghost" size="sm" icon-only :disabled="disabled" @click="remove_entry(index)">
        <Icon icon="lucide:x" width="14" />
      </Button>
    </div>
    <Button variant="secondary" size="xs" class="field-add" :disabled="disabled" @click="add_entry">
      <Icon icon="lucide:plus" width="13" />
      {{ t('ui.form_editor_add_entry') }}
    </Button>
  </div>
</template>

<style scoped>
.field-map {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.field-map-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  width: 100%;
}

.field-map-key {
  flex: 1;
}

.field-map-arrow {
  flex: 0 0 auto;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.field-map-value {
  flex: 2;
}

.field-map-list {
  display: flex;
  flex: 2;
  flex-direction: column;
  gap: var(--space-1);
}

.field-map-list-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.field-map-list-row :deep(.ui-input) {
  flex: 1;
}

.field-add {
  align-self: flex-end;
}
</style>
