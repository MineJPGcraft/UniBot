/**
 * 消息**命名空间树**的共享工具。
 *
 * 树节点形如 `{ name, path, label, count, modified_count, children, items }`；
 * 叶子消息项形如 `{ key, path, value, base_value, is_list, placeholders, modified }`。
 */
import { deep_equal } from '@/utils/equals'

/** 深度遍历命名空间树，对每个叶子消息项执行回调。 */
export function each_message_item(nodes, callback) {
  for (const node of nodes) {
    for (const item of node.items) callback(item)
    each_message_item(node.children, callback)
  }
}

/** 某条消息的生效值：草稿优先，否则用服务端下发的生效值。 */
export function message_value(item, draft) {
  return item.key in draft ? draft[item.key] : item.value
}

/** 某条消息是否相对默认译文被改动（即用户已覆盖）。 */
export function message_modified(item, draft) {
  return !deep_equal(message_value(item, draft), item.base_value)
}

/** 某条消息是否有**未保存**的草稿改动（草稿值 ≠ 服务端生效值）。 */
export function message_pending(item, draft) {
  return item.key in draft && !deep_equal(draft[item.key], item.value)
}

/** 统计每个命名空间**子树内的未保存改动数**：返回 `{ 路径: 数量 }`（无改动不出现在结果中）。 */
export function pending_edit_counts(nodes, draft) {
  const counts = {}
  function walk(node) {
    let count = 0
    for (const item of node.items) {
      if (message_pending(item, draft)) count += 1
    }
    for (const child of node.children) count += walk(child)
    if (count > 0) counts[node.path] = count
    return count
  }
  for (const node of nodes) walk(node)
  return counts
}

/** 收集树中所有**含子节点**的命名空间路径（供「全部展开 / 折叠」使用）。 */
export function namespace_paths(nodes) {
  const paths = []
  for (const node of nodes) {
    paths.push(node.path)
    if (node.children.length) paths.push(...namespace_paths(node.children))
  }
  return paths
}

/** 按路径在树中查找命名空间节点（找不到返回 null）。 */
export function find_node(nodes, path) {
  for (const node of nodes) {
    if (node.path === path) return node
    const found = find_node(node.children, path)
    if (found) return found
  }
  return null
}
