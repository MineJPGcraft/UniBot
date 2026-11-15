<script setup>
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from 'reka-ui'
import { Icon } from '@iconify/vue'

const open = defineModel({ type: Boolean, default: false })

defineProps({
  disabled: { type: Boolean, default: false },
})
</script>

<template>
  <CollapsibleRoot
    :open="open"
    class="ui-collapsible"
    :disabled="disabled"
    @update:open="(value) => (open = value)"
  >
    <CollapsibleTrigger class="ui-collapsible-trigger">
      <slot name="trigger" :open="open">
        <Icon
          :icon="open ? 'lucide:chevron-down' : 'lucide:chevron-right'"
          width="14"
          class="ui-collapsible-chevron"
        />
        <span><slot /></span>
      </slot>
    </CollapsibleTrigger>
    <CollapsibleContent class="ui-collapsible-content">
      <slot name="content" />
    </CollapsibleContent>
  </CollapsibleRoot>
</template>

<style scoped>
.ui-collapsible {
  width: 100%;
}

.ui-collapsible-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition:
    border-color var(--transition),
    background-color var(--transition);
}

.ui-collapsible-trigger:hover {
  border-color: var(--border-strong);
  background: var(--surface-soft);
}

.ui-collapsible-chevron {
  flex: 0 0 auto;
  color: var(--text-muted);
}

.ui-collapsible-content {
  overflow: hidden;
  margin-top: var(--space-2);
}
</style>
