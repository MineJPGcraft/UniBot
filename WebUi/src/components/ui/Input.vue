<script setup>
const model = defineModel({ type: [String, Number], default: '' })

defineProps({
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  min: { type: [Number, String], default: undefined },
  max: { type: [Number, String], default: undefined },
  step: { type: [Number, String], default: undefined },
})
</script>

<template>
  <input
    v-model="model"
    class="ui-input"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :min="min"
    :max="max"
    :step="step"
  />
</template>

<style scoped>
.ui-input {
  width: 100%;
  height: 34px;
  padding: 0 var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.ui-input::placeholder {
  color: var(--text-muted);
}

.ui-input:hover:not(:disabled) {
  border-color: var(--border-strong);
}

.ui-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.ui-input:disabled {
  background: var(--surface-sunken);
  color: var(--text-muted);
  cursor: not-allowed;
}
</style>
