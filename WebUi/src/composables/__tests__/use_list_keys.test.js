import { describe, expect, it } from 'vitest'
import { use_list_keys } from '@/composables/use_list_keys'

describe('use_list_keys', () => {
  it('首次取值时按顺序补发稳定 key', () => {
    const { key_for } = use_list_keys()
    const first = key_for(0)
    const second = key_for(1)
    expect(first).not.toBe(second)
    // 重复取同一位返回同一 key
    expect(key_for(0)).toBe(first)
    expect(key_for(1)).toBe(second)
  })

  it('跳跃取值时补齐中间位置的 key', () => {
    const { key_for } = use_list_keys()
    key_for(3)
    expect(key_for(0)).not.toBe(key_for(1))
    expect(key_for(3)).not.toBe(key_for(0))
  })

  it('删除中间项后，后续项不会继承被删项的 key', () => {
    const { key_for, remove } = use_list_keys()
    const keys = [key_for(0), key_for(1), key_for(2)]
    remove(1)
    // 删除后原 index 2 的项移动到 index 1，其 key 应为原第三项的 key
    expect(key_for(1)).toBe(keys[2])
    // 新补齐的 index 2 不会是已删除的 key
    expect(key_for(2)).not.toBe(keys[1])
  })

  it('移动项时 key 随条目搬移（折叠等行内状态跟随）', () => {
    const { key_for, move } = use_list_keys()
    const keys = [key_for(0), key_for(1), key_for(2)]
    // move 为交换语义（与 SchemaField 的列表项交换一致）
    move(0, 2)
    expect([key_for(0), key_for(1), key_for(2)]).toEqual([keys[2], keys[1], keys[0]])
  })

  it('越界移动不做任何改动', () => {
    const { key_for, move } = use_list_keys()
    const keys = [key_for(0), key_for(1)]
    move(0, 5)
    move(1, -1)
    expect([key_for(0), key_for(1)]).toEqual(keys)
  })
})
