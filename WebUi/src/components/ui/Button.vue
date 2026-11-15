<script setup>
import Spinner from './Spinner.vue'

defineProps({
  variant: { type: String, default: 'secondary' }, // primary | secondary | ghost | danger
  size: { type: String, default: 'md' }, // md | sm | xs
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  iconOnly: { type: Boolean, default: false },
})
</script>

<template>
  <button
    class="ui-button"
    :class="[
      `ui-button--${variant}`,
      { [`ui-button--${size}`]: size !== 'md', 'ui-button--icon': iconOnly },
    ]"
    :disabled="disabled || loading"
  >
    <Spinner v-if="loading" :size="14" />
    <slot />
  </button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 34px;
  padding: 0 var(--space-4);
  border-radius: var(--radius);
  border: 1px solid transparent;
  font-size: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
  user-select: none;
  transition:
    background-color var(--transition),
    border-color var(--transition),
    color var(--transition),
    box-shadow var(--transition);
}

.ui-button:disabled,
.ui-button[data-disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}

.ui-button--primary {
  background: var(--accent);
  color: #ffffff;
}

.ui-button--primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.ui-button--secondary {
  background: var(--surface);
  border-color: var(--border);
  color: var(--text-secondary);
}

.ui-button--secondary:hover:not(:disabled) {
  border-color: var(--border-strong);
  color: var(--text);
}

.ui-button--ghost {
  background: transparent;
  color: var(--text-secondary);
}

.ui-button--ghost:hover:not(:disabled) {
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text);
}

.ui-button--danger {
  background: var(--danger);
  color: #ffffff;
}

.ui-button--danger:hover:not(:disabled) {
  background: var(--danger-hover);
}

.ui-button--sm {
  height: 28px;
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
}

/* 内联于字段行 / 列表末尾的最小尺寸（图标与文字间距同步收紧） */
.ui-button--xs {
  gap: var(--space-1);
  height: 24px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
}

.ui-button--icon {
  width: 34px;
  padding: 0;
}

.ui-button--icon.ui-button--sm {
  width: 28px;
}

.ui-button--icon.ui-button--xs {
  width: 24px;
}

.ui-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
</style>
