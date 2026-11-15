/**
 * 结构化深比较（纯函数）。
 *
 * 用于「草稿 vs 原值」的变更检测，替代原先的 `JSON.stringify(a) !== JSON.stringify(b)`：
 * - 引用相等（`===`）直接短路，标量字段零开销；
 * - 不为大对象 / 数组分配中间字符串；
 * - 对象键顺序不影响结果（JSON 比较会因此误报改动）。
 */

/** 判断两个值是否结构相等（仅适用于 JSON 兼容数据） */
export function deep_equal(left, right) {
  if (left === right) return true
  if (left == null || right == null) return false
  if (typeof left !== 'object' || typeof right !== 'object') return false

  const left_is_array = Array.isArray(left)
  if (left_is_array !== Array.isArray(right)) return false

  if (left_is_array) {
    if (left.length !== right.length) return false
    for (let index = 0; index < left.length; index += 1) {
      if (!deep_equal(left[index], right[index])) return false
    }
    return true
  }

  const left_keys = Object.keys(left)
  if (left_keys.length !== Object.keys(right).length) return false
  for (const key of left_keys) {
    if (!Object.prototype.hasOwnProperty.call(right, key)) return false
    if (!deep_equal(left[key], right[key])) return false
  }
  return true
}

/**
 * 创建「按字段缓存」的变更判定器：同一字段的原值 / 草稿值引用均未变时复用上次结果。
 *
 * 表单草稿按不可变方式更新（只有被编辑字段的引用会变），因此输入时绝大多数字段
 * 命中缓存，比较开销从「整表 O(字段数)」降为「改动字段 O(1)」。
 *
 * @returns {(key: string, original: any, current: any) => boolean} 该字段是否已改动
 */
export function create_change_detector() {
  const cache = new Map()
  return function is_changed(key, original, current) {
    const cached = cache.get(key)
    if (cached && cached.original === original && cached.current === current) return cached.changed
    const changed = !deep_equal(original, current)
    cache.set(key, { original, current, changed })
    return changed
  }
}
