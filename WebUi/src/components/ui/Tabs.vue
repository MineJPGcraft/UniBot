<script setup>
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui'
import { Icon } from '@iconify/vue'

const model = defineModel({ type: String, default: '' })

defineProps({
  /** 标签页：[{ value, label, icon }] */
  tabs: { type: Array, required: true },
})
</script>

<template>
  <TabsRoot v-model="model">
    <TabsList class="ui-tabs-list">
      <TabsTrigger v-for="tab in tabs" :key="tab.value" class="ui-tabs-trigger" :value="tab.value">
        <Icon v-if="tab.icon" :icon="tab.icon" width="14" />
        {{ tab.label }}
      </TabsTrigger>
    </TabsList>
    <TabsContent v-for="tab in tabs" :key="tab.value" class="ui-tabs-content" :value="tab.value">
      <slot :name="tab.value" />
    </TabsContent>
  </TabsRoot>
</template>

<style scoped>
.ui-tabs-list {
  display: inline-flex;
  gap: var(--space-1);
  padding: var(--space-1);
  background: color-mix(in srgb, var(--text) 4%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.ui-tabs-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 30px;
  padding: 0 var(--space-4);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.ui-tabs-trigger:hover {
  color: var(--text);
}

.ui-tabs-trigger[data-state='active'] {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow);
}

.ui-tabs-content {
  margin-top: var(--space-4);
  outline: none;
}

.ui-tabs-content[data-state='inactive'] {
  display: none;
}
</style>
