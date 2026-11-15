<script setup>
/**
 * 配置中心：分组 / 条目导航（左侧 sidebar）。
 *
 * 同时服务「配置分组」与「扩展条目」两种列表：分组用 `keys` 判断组内是否有改动
 * 并显示黄点；扩展条目没有 `keys`，其改动状态由调用方经 `changedIds` 传入。
 */
defineProps({
  /** 列表：[{ id, name, keys? }] */
  items: { type: Array, required: true },
  /** 当前选中的 id */
  activeId: { type: String, default: '' },
  /** 有改动的 id 集合（Set），命中即黄点（扩展条目用） */
  changedIds: { type: Set, default: () => new Set() },
  /** 有改动字段的 key 集合（Set），用于分组形态的黄点判定 */
  changedKeys: { type: Set, default: () => new Set() },
})

defineEmits(['select'])

/** 条目是否需要黄点：直接命中 changedIds，或组内存在改动字段 */
function is_changed(item, changed_ids, changed_keys) {
  if (changed_ids.has(item.id)) return true
  if (!Array.isArray(item.keys)) return false
  return item.keys.some((key) => changed_keys.has(key))
}
</script>

<template>
  <nav class="group-nav card">
    <button
      v-for="item in items"
      :key="item.id || item.name"
      class="group-item"
      :class="{ 'group-item--active': activeId === item.id }"
      @click="emit('select', item.id)"
    >
      <span class="group-item-name">{{ item.name }}</span>
      <span v-if="is_changed(item, changedIds, changedKeys)" class="group-dot" />
    </button>
  </nav>
</template>

<style scoped>
.group-nav {
  padding: var(--space-2);
  position: sticky;
  top: var(--space-4);
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-muted);
  text-align: left;
  transition:
    background-color var(--transition),
    color var(--transition);
}

.group-item:hover {
  background: color-mix(in srgb, var(--text) 4%, transparent);
  color: var(--text);
}

.group-item--active {
  background: var(--accent-soft);
  color: var(--accent);
}

.group-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--warning);
}
</style>
