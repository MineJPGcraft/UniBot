<script setup>
/**
 * 平台列表字段控件：`平台:目标` 形式的字符串列表。
 *
 * 选项来自 schema 的 `x-options`（后端按平台适配器目录下发），
 * 每项拆成「平台下拉 + 目标输入」两个控件，提交时重新拼回 `平台:目标`。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_list_keys } from '@/composables/use_list_keys'
import { clone } from '@/utils/schema_form'
import Input from '../Input.vue'
import Button from '../Button.vue'
import Select from '../Select.vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  /** 可选平台（`{ value, label }` 数组） */
  options: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const list_keys = use_list_keys()

const items = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))

/** `平台:目标` 形式的单项拆分；无分隔符时按目标文本处理 */
function split_item(item, fallback = '') {
  const separator = String(item || '').indexOf(':')
  if (separator < 0) return { platform: fallback, target: String(item || '') }
  return { platform: item.slice(0, separator), target: item.slice(separator + 1) }
}

function update_item(index, property, value) {
  const next = clone(items.value)
  const fallback = props.options[0]?.value || ''
  const entry = split_item(next[index], fallback)
  entry[property] = value
  next[index] = `${entry.platform}:${entry.target}`
  emit('update:modelValue', next)
}

function add_item() {
  const platform = props.options[0]?.value || ''
  emit('update:modelValue', [...items.value, `${platform}:`])
}

function remove_item(index) {
  const next = clone(items.value)
  next.splice(index, 1)
  list_keys.remove(index)
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="field-list-editor">
    <div v-for="(item, index) in items" :key="list_keys.key_for(index)" class="field-platform-row">
      <Select
        :model-value="split_item(item, options[0]?.value).platform"
        :options="options"
        :disabled="disabled"
        @update:model-value="(value) => update_item(index, 'platform', value)"
      />
      <Input
        :model-value="split_item(item).target"
        :placeholder="t('ui.form_platform_target_placeholder')"
        :disabled="disabled"
        @update:model-value="(value) => update_item(index, 'target', value)"
      />
      <Button variant="ghost" size="sm" icon-only :disabled="disabled" @click="remove_item(index)">
        <Icon icon="lucide:x" width="14" />
      </Button>
    </div>
    <Button variant="secondary" size="xs" class="field-add" :disabled="disabled" @click="add_item">
      <Icon icon="lucide:plus" width="13" />
      {{ t('ui.form_add_item') }}
    </Button>
  </div>
</template>

<style scoped>
.field-list-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.field-platform-row {
  display: grid;
  grid-template-columns: 132px 1fr auto;
  gap: var(--space-1);
  width: 100%;
}

.field-platform-row :deep(.ui-select-trigger) {
  width: 100%;
  min-width: 0;
}

.field-add {
  align-self: flex-end;
}
</style>
