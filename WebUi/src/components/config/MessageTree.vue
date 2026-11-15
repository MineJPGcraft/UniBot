<script setup>
/**
 * 消息文本**命名空间树**编辑器（容器）。
 *
 * - 按翻译键的点路径（如 `core.commands.luck.result`）折叠为可展开/折叠的命名空间树；
 * - 顶部提供搜索（按命名空间路径 / 键名 / 消息内容过滤，命中时自动展开）与全部展开/折叠；
 * - 未保存改动数按树统计（`pending_edit_counts`），驱动命名空间节点上的提示点；
 * - 叶子消息由 MessageTreeRow 渲染，草稿值经 `update` 事件冒泡给父级 store。
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import MessageTreeNode from '@/components/config/MessageTreeNode.vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'
import { use_message_editor } from '@/composables/use_message_editor'
import {
  each_message_item,
  message_value,
  namespace_paths,
  pending_edit_counts,
} from '@/utils/message_tree'

const props = defineProps({
  /** 命名空间树：[{ name, path, label, count, modified_count, children, items }] */
  tree: { type: Array, default: () => [] },
  /** 草稿：键 → 草稿值 */
  draft: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update'])

const { t } = useI18n()
const { raw_mode } = use_message_editor()

/** 关键词命中判断：命名空间路径、键名或消息内容任一包含即算命中。 */
function node_matches(node, needle) {
  if (node.path.toLowerCase().includes(needle)) return true
  let hit = false
  each_message_item([node], (item) => {
    if (hit) return
    if (
      item.key.toLowerCase().includes(needle) ||
      String(message_value(item, props.draft)).toLowerCase().includes(needle)
    ) {
      hit = true
    }
  })
  return hit
}

/** 保留子树中有命中的节点（无搜索词时原样返回）。 */
function filter_tree(nodes, needle) {
  if (!needle) return nodes
  const result = []
  for (const node of nodes) {
    if (!node_matches(node, needle)) continue
    if (node.path.toLowerCase().includes(needle)) {
      result.push(node)
      continue
    }
    result.push({
      ...node,
      children: filter_tree(node.children, needle),
      items: node.items.filter(
        (item) =>
          item.key.toLowerCase().includes(needle) ||
          String(message_value(item, props.draft)).toLowerCase().includes(needle),
      ),
    })
  }
  return result
}

const query = ref('')
const visible_tree = computed(() => filter_tree(props.tree, query.value.trim().toLowerCase()))

const visible_count = computed(() => {
  let count = 0
  each_message_item(visible_tree.value, () => {
    count += 1
  })
  return count
})

/** 各命名空间子树内的未保存改动数（`{ path: count }`），驱动节点上的提示点 */
const pending_counts = computed(() => pending_edit_counts(props.tree, props.draft))

// 展开状态：`{ 命名空间路径: true }` 映射；默认展开顶层命名空间。
const expanded = ref({})

watch(
  () => props.tree,
  (tree) => {
    // 语言切换时会整体替换树：保留仍然存在的展开路径，并默认展开顶层命名空间
    const valid = new Set(namespace_paths(tree))
    const next = {}
    for (const path of Object.keys(expanded.value)) {
      if (valid.has(path)) next[path] = true
    }
    for (const node of tree) next[node.path] = true
    expanded.value = next
  },
  { immediate: true },
)

function toggle(path) {
  const next = { ...expanded.value }
  if (next[path]) delete next[path]
  else next[path] = true
  expanded.value = next
}

function expand_all() {
  const next = {}
  for (const path of namespace_paths(props.tree)) next[path] = true
  expanded.value = next
}

function collapse_all() {
  expanded.value = {}
}

function on_update(key, value) {
  emit('update', key, value)
}
</script>

<template>
  <div v-if="tree.length" class="message-tree card">
    <div class="tree-toolbar">
      <Input v-model="query" :placeholder="t('config_view.messages_search')" class="tree-search" />
      <span class="tree-count">
        {{ t('config_view.messages_count', { count: visible_count }) }}
      </span>
      <div class="tree-toolbar-actions">
        <label class="tree-mode">
          <Switch v-model="raw_mode" />
          {{ t('config_view.messages_view_raw') }}
        </label>
        <button type="button" class="tree-tool" @click="expand_all">
          <Icon icon="lucide:unfold-vertical" width="14" />
          {{ t('config_view.messages_expand_all') }}
        </button>
        <button type="button" class="tree-tool" @click="collapse_all">
          <Icon icon="lucide:fold-vertical" width="14" />
          {{ t('config_view.messages_collapse_all') }}
        </button>
      </div>
    </div>

    <p v-if="!visible_count" class="message-empty">
      {{ t('config_view.messages_no_match') }}
    </p>

    <div v-else class="tree-body">
      <MessageTreeNode
        v-for="node in visible_tree"
        :key="node.path"
        :node="node"
        :draft="draft"
        :pending-counts="pending_counts"
        :depth="0"
        :expanded="expanded"
        :query="query.trim()"
        @update="on_update"
        @toggle="toggle"
      />
    </div>
  </div>

  <p v-else class="message-empty">{{ t('config_view.messages_empty') }}</p>
</template>

<style scoped>
.message-tree {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
}

.tree-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.tree-search {
  max-width: 320px;
}

.tree-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.tree-toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-left: auto;
}

.tree-mode {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}

.tree-tool {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  color: var(--text-muted);
  cursor: pointer;
}

.tree-tool:hover {
  background: var(--hover);
  color: var(--text);
}

.tree-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.message-empty {
  padding: var(--space-6);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-muted);
}
</style>
