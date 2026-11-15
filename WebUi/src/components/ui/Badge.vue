<script setup>
defineProps({
  variant: { type: String, default: 'neutral' }, // neutral | success | warning | danger | accent
})
</script>

<template>
  <span class="ui-badge" :class="`ui-badge--${variant}`">
    <slot />
  </span>
</template>

<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  height: 20px;
  padding: 0 var(--space-2);
  border-radius: 4px;
  font-size: var(--text-xs);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.ui-badge--neutral {
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text-secondary);
}

.ui-badge--success {
  background: var(--success-soft);
  color: var(--success);
}

.ui-badge--warning {
  background: var(--warning-soft);
  color: var(--warning);
}

.ui-badge--danger {
  background: var(--danger-soft);
  color: var(--danger);
}

.ui-badge--accent {
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
