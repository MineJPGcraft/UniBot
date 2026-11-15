<script setup>
import {
  DropdownMenuRoot,
  DropdownMenuTrigger,
  DropdownMenuPortal,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from 'reka-ui'
import { Icon } from '@iconify/vue'

defineProps({
  /** 菜单项：[{ label, icon, danger, separator, disabled, on_select }] */
  items: { type: Array, required: true },
  align: { type: String, default: 'end' },
})
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger>
      <slot name="trigger" />
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent class="ui-dropdown-content" :align="align" :side-offset="4">
        <DropdownMenuLabel v-if="$slots.label" class="ui-dropdown-label">
          <slot name="label" />
        </DropdownMenuLabel>
        <template v-for="(item, index) in items">
          <DropdownMenuSeparator
            v-if="item.separator"
            :key="`separator-${index}`"
            class="ui-dropdown-separator"
          />
          <DropdownMenuItem
            v-else
            :key="`item-${index}`"
            class="ui-dropdown-item"
            :class="{ 'ui-dropdown-item--danger': item.danger }"
            :disabled="item.disabled"
            @select="item.on_select?.()"
          >
            <Icon v-if="item.icon" :icon="item.icon" width="14" />
            {{ item.label }}
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

<style>
@keyframes dropdown-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
}

.ui-dropdown-content {
  position: relative;
  min-width: 168px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-1);
  z-index: var(--z-dropdown);
  animation: dropdown-in var(--transition);
}
</style>

<style scoped>
.ui-dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  transition: background-color var(--transition);
}

.ui-dropdown-item[data-highlighted] {
  background: var(--accent-soft);
  color: var(--accent);
  outline: none;
}

.ui-dropdown-item--danger {
  color: var(--danger);
}

.ui-dropdown-item--danger[data-highlighted] {
  background: var(--danger-soft);
  color: var(--danger);
}

.ui-dropdown-separator {
  height: 1px;
  margin: var(--space-1) 0;
  background: var(--border);
}

.ui-dropdown-label {
  padding: var(--space-2) var(--space-3) var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
