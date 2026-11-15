import { ref } from 'vue'

/**
 * 可编辑列表的稳定 key 簿记。
 *
 * 列表项无自然 id（可增删、内容可重复），直接用下标作 key 会导致删除中间项时
 * 输入框内容串位。本 composable 为每个位置分配自增 id，渲染时按需补齐；
 * 增删移动时同步维护簿记，使输入框内容与行内状态（如折叠）始终跟随条目本身。
 */
export function use_list_keys() {
  const keys = ref([])
  let sequence = 0

  /** 取第 index 位的稳定 key，缺失时补发（渲染期调用） */
  function key_for(index) {
    while (keys.value.length <= index) {
      sequence += 1
      keys.value.push(`list-item-${sequence}`)
    }
    return keys.value[index]
  }

  /** 删除第 index 位（同步移除其 key） */
  function remove(index) {
    keys.value.splice(index, 1)
  }

  /** 移动第 index 位到 target 位（同步搬移 key，使行内状态跟随条目） */
  function move(index, target) {
    if (target < 0 || target >= keys.value.length) return
    ;[keys.value[index], keys.value[target]] = [keys.value[target], keys.value[index]]
  }

  return { key_for, remove, move }
}
