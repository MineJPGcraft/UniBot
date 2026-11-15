<script setup>
/**
 * 字符串列表字段控件。
 *
 * 无自然 id 的可编辑列表，用 `use_list_keys` 维护稳定 key：
 * 删除 / 移动中间项时输入框内容与行内状态不串位。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_list_keys } from '@/composables/use_list_keys'
import { clone } from '@/utils/schema_form'
import Input from '../Input.vue'
import Button from '../Button.vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const list_keys = use_list_keys()

const items = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))

function update_item(index, value) {
  const next = clone(items.value)
  next[index] = value
  emit('update:modelValue', next)
}

function add_item() {
  emit('update:modelValue', [...items.value, ''])
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
    <div v-for="(item, index) in items" :key="list_keys.key_for(index)" class="field-list-row">
      <Input
        :model-value="item"
        :disabled="disabled"
        @update:model-value="(value) => update_item(index, value)"
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

.field-list-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  width: 100%;
}

.field-list-row :deep(.ui-input) {
  flex: 1;
}

.field-add {
  align-self: flex-end;
}
</style>
