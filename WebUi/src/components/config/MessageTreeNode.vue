<script setup>
/**
 * 消息**命名空间树**的单个节点（递归组件）。
 *
 * - 节点头部可点击展开/折叠，显示命名空间名、完整路径、子树消息数与**未保存改动**指示点；
 * - 展开后先渲染本层叶子消息（MessageTreeRow），再递归渲染子命名空间；
 * - 搜索时（`query` 非空）所有节点自动展开，方便查看命中项。
 */
import { Icon } from '@iconify/vue'
import MessageTreeRow from '@/components/config/MessageTreeRow.vue'

const props = defineProps({
  /** 命名空间节点：{ name, path, label, count, modified_count, children, items } */
  node: { type: Object, required: true },
  /** 草稿：键 → 草稿值 */
  draft: { type: Object, default: () => ({}) },
  /** 各命名空间子树内的未保存改动数：`{ path: count }` */
  pendingCounts: { type: Object, default: () => ({}) },
  /** 树的当前层数（根为 0，用于缩进） */
  depth: { type: Number, default: 0 },
  /** 已展开的命名空间路径映射 `{ path: true }` */
  expanded: { type: Object, required: true },
  /** 当前搜索词（非空时强制展开） */
  query: { type: String, default: '' },
})

const emit = defineEmits(['update', 'toggle'])

function is_expanded() {
  return props.query !== '' || props.node.path in props.expanded
}

function on_update(key, value) {
  emit('update', key, value)
}
</script>

<template>
  <div class="tree-node">
    <button
      type="button"
      class="node-head"
      :style="{ '--depth': depth }"
      @click="emit('toggle', node.path)"
    >
      <Icon
        :icon="is_expanded() ? 'lucide:chevron-down' : 'lucide:chevron-right'"
        width="14"
        class="node-chevron"
      />
      <span class="node-label">{{ node.label }}</span>
      <code class="node-path">{{ node.path }}</code>
      <span v-if="pendingCounts[node.path]" class="node-dot" />
      <span class="node-count">{{ node.count }}</span>
    </button>

    <template v-if="is_expanded()">
      <div v-if="node.items.length" class="node-items" :style="{ '--depth': depth + 1 }">
        <MessageTreeRow
          v-for="item in node.items"
          :key="item.key"
          :item="item"
          :draft="draft"
          @update="on_update"
        />
      </div>

      <MessageTreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :draft="draft"
        :pending-counts="pendingCounts"
        :depth="depth + 1"
        :expanded="expanded"
        :query="query"
        @update="on_update"
        @toggle="emit('toggle', $event)"
      />
    </template>
  </div>
</template>

<style scoped>
.tree-node {
  display: flex;
  flex-direction: column;
}

.node-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-2) var(--space-2)
    calc(var(--space-2) + var(--depth) * var(--space-4));
  border-radius: var(--radius);
  text-align: left;
  cursor: pointer;
  transition: background-color var(--transition);
}

.node-head:hover {
  background: var(--hover);
}

.node-chevron {
  flex-shrink: 0;
  color: var(--text-muted);
}

.node-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.node-path {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--warning);
  flex-shrink: 0;
}

.node-count {
  margin-left: auto;
  flex-shrink: 0;
  padding: 0 var(--space-2);
  height: 18px;
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius);
  background: var(--hover);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.node-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-1) 0 var(--space-2);
  padding-left: calc(var(--space-2) + var(--depth) * var(--space-4));
}
</style>
