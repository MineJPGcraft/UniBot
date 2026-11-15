<script setup>
import { Icon } from '@iconify/vue'
import { use_toast } from '@/composables/use_toast'

const { toast_list, dismiss_toast } = use_toast()

const icon_map = {
  success: 'lucide:check-circle-2',
  error: 'lucide:x-circle',
  info: 'lucide:info',
}
</script>

<template>
  <div class="toast-viewport">
    <transition-group name="toast-move">
      <div
        v-for="toast in toast_list"
        :key="toast.id"
        class="toast-item"
        :class="`toast-item--${toast.type}`"
        @click="dismiss_toast(toast.id)"
      >
        <Icon :icon="icon_map[toast.type]" width="16" class="toast-icon" />
        <span>{{ toast.message }}</span>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-viewport {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  max-width: 360px;
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  pointer-events: auto;
  cursor: pointer;
}

.toast-item--success {
  border-left-color: var(--success);
}

.toast-item--success .toast-icon {
  color: var(--success);
}

.toast-item--error {
  border-left-color: var(--danger);
}

.toast-item--error .toast-icon {
  color: var(--danger);
}

.toast-item--info .toast-icon {
  color: var(--accent);
}

.toast-move-enter-active,
.toast-move-leave-active {
  transition:
    opacity 180ms ease-out,
    transform 180ms ease-out;
}

.toast-move-enter-from,
.toast-move-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
