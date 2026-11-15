<script setup>
const model = defineModel({ type: String, default: '' })

defineProps({
  placeholder: { type: String, default: '' },
  rows: { type: Number, default: 3 },
})
</script>

<template>
  <textarea v-model="model" class="ui-textarea" :placeholder="placeholder" :rows="rows" />
</template>

<style scoped>
.ui-textarea {
  width: 100%;
  min-height: 76px;
  padding: var(--space-2) var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  resize: vertical;
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.ui-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
</style>
