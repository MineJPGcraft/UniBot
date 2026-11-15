<script setup>
defineProps({
  size: { type: Number, default: 16 },
})
</script>

<template>
  <span class="ui-spinner" :style="{ width: `${size}px`, height: `${size}px` }" />
</template>

<style scoped>
.ui-spinner {
  display: inline-block;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spinner-rotate 700ms linear infinite;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
