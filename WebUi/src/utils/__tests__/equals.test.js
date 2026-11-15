import { describe, expect, it } from 'vitest'
import { create_change_detector, deep_equal } from '@/utils/equals'

describe('deep_equal', () => {
  it('标量与同引用直接判定', () => {
    expect(deep_equal(1, 1)).toBe(true)
    expect(deep_equal('a', 'a')).toBe(true)
    expect(deep_equal(null, null)).toBe(true)
    expect(deep_equal(1, '1')).toBe(false)
    expect(deep_equal(null, undefined)).toBe(false)
  })

  it('数组逐项比较', () => {
    expect(deep_equal(['a', 'b'], ['a', 'b'])).toBe(true)
    expect(deep_equal(['a', 'b'], ['a', 'c'])).toBe(false)
    expect(deep_equal(['a'], ['a', 'b'])).toBe(false)
    expect(deep_equal([], {})).toBe(false)
  })

  it('对象忽略键顺序、逐项比较', () => {
    expect(deep_equal({ a: 1, b: [2] }, { b: [2], a: 1 })).toBe(true)
    expect(deep_equal({ a: 1 }, { a: 1, b: 2 })).toBe(false)
    expect(deep_equal({ a: 1 }, { a: 2 })).toBe(false)
  })

  it('嵌套结构与 JSON 比较语义一致（除键顺序）', () => {
    const value = { server: { urls: { main: ['ws://a'] } } }
    expect(deep_equal(value, { server: { urls: { main: ['ws://a'] } } })).toBe(true)
    expect(deep_equal(value, { server: { urls: { main: ['ws://b'] } } })).toBe(false)
  })
})

describe('create_change_detector 按字段缓存', () => {
  it('未改动字段第二次比较命中缓存，不再重新比较', () => {
    const is_changed = create_change_detector()
    const original = { deep: { nested: 1 } }
    const current = JSON.parse(JSON.stringify(original))

    expect(is_changed('key', original, current)).toBe(false)

    // 破坏内部数据：若仍命中缓存，结果应保持为「未改动」
    current.deep.nested = 999
    expect(is_changed('key', original, current)).toBe(false)
  })

  it('引用变化时重新比较', () => {
    const is_changed = create_change_detector()
    const original = { nested: 1 }
    const current = { nested: 1 }

    expect(is_changed('key', original, current)).toBe(false)
    expect(is_changed('key', original, { nested: 2 })).toBe(true)
  })

  it('不同字段各自缓存，互不影响', () => {
    const is_changed = create_change_detector()
    expect(is_changed('a', 1, 2)).toBe(true)
    expect(is_changed('b', 1, 1)).toBe(false)
    expect(is_changed('a', 1, 2)).toBe(true)
  })
})
