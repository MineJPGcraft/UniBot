<script setup>
import { Icon } from '@iconify/vue'

defineProps({
  icon: { type: String, default: 'lucide:inbox' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="empty-state">
    <Icon :icon="icon" width="40" class="empty-icon" />
    <div class="empty-title">{{ title }}</div>
    <div v-if="description" class="empty-desc">{{ description }}</div>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  color: var(--text-muted);
  text-align: center;
}

.empty-icon {
  color: var(--border-strong);
  margin-bottom: var(--space-2);
}

.empty-title {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--text-secondary);
}

.empty-desc {
  font-size: var(--text-sm);
  max-width: 360px;
}
</style>
