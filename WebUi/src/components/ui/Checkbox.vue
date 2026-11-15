<script setup>
import { CheckboxRoot, CheckboxIndicator } from 'reka-ui'
import { Icon } from '@iconify/vue'

const checked = defineModel({ type: Boolean, default: false })

defineProps({
  disabled: { type: Boolean, default: false },
})
</script>

<template>
  <CheckboxRoot
    :checked="checked"
    class="ui-checkbox"
    :disabled="disabled"
    @update:checked="(value) => (checked = value)"
  >
    <CheckboxIndicator>
      <Icon icon="lucide:check" width="12" />
    </CheckboxIndicator>
  </CheckboxRoot>
</template>

<style scoped>
.ui-checkbox {
  box-sizing: border-box;
  display: inline-flex;
  flex: 0 0 16px;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  background: var(--surface);
  color: #ffffff;
  cursor: pointer;
  transition:
    background-color var(--transition),
    border-color var(--transition),
    box-shadow var(--transition);
}

.ui-checkbox[data-state='checked'] {
  background: var(--accent);
  border-color: var(--accent);
}

.ui-checkbox:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.ui-checkbox:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
