<script setup>
import { SwitchRoot, SwitchThumb } from 'reka-ui'

const checked = defineModel({ type: Boolean, default: false })

defineProps({
  disabled: { type: Boolean, default: false },
})
</script>

<template>
  <SwitchRoot v-model="checked" class="ui-switch" :disabled="disabled">
    <SwitchThumb class="ui-switch-thumb" />
  </SwitchRoot>
</template>

<style scoped>
.ui-switch {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: var(--border-strong);
  flex-shrink: 0;
  cursor: pointer;
  transition: background-color var(--transition);
}

.ui-switch[data-state='checked'] {
  background: var(--accent);
}

.ui-switch[data-disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}

.ui-switch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--switch-knob);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.2);
  transition: transform var(--transition);
}

.ui-switch[data-state='checked'] .ui-switch-thumb {
  transform: translateX(16px);
}
</style>
