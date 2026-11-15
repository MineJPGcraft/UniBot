<script setup>
import { ProgressRoot, ProgressIndicator } from 'reka-ui'

defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
})
</script>

<template>
  <ProgressRoot class="ui-progress" :model-value="value" :max="max">
    <ProgressIndicator
      class="ui-progress-indicator"
      :style="{ width: `${max > 0 ? Math.min(100, (value / max) * 100) : 0}%` }"
    />
  </ProgressRoot>
</template>

<style scoped>
.ui-progress {
  position: relative;
  height: 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--text) 6%, transparent);
  overflow: hidden;
}

.ui-progress-indicator {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: width 300ms ease-out;
}
</style>
