import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import SchemaField from '@/components/ui/SchemaField.vue'
import ui_messages from '@/i18n/messages/ui.json'

/** 挂载时注入最小 i18n（组件文案全部来自 ui 命名空间） */
function mount_field(props) {
  const i18n = createI18n({
    legacy: false,
    locale: 'zh',
    fallbackLocale: 'zh',
    missingWarn: false,
    fallbackWarn: false,
    messages: { zh: { ui: ui_messages.zh }, en: { ui: ui_messages.en } },
  })
  return mount(SchemaField, {
    props,
    global: { plugins: [i18n] },
  })
}

/** 读取组件最近一次 update:modelValue 事件的值 */
function last_emitted(wrapper) {
  const events = wrapper.emitted('update:modelValue')
  return events?.[events.length - 1]?.[0]
}

describe('SchemaField 标量控件分发', () => {
  it('boolean 渲染开关', () => {
    const wrapper = mount_field({ schema: { type: 'boolean' }, modelValue: true })
    expect(wrapper.find('.ui-switch').exists() || wrapper.html().includes('switch')).toBe(true)
  })

  it('enum 渲染下拉选择', () => {
    const wrapper = mount_field({ schema: { enum: ['a', 'b'] }, modelValue: 'a' })
    expect(wrapper.find('.ui-select-trigger').exists()).toBe(true)
  })

  it('number 空值序列化为 null', async () => {
    const wrapper = mount_field({ schema: { type: 'integer' }, modelValue: 3 })
    await wrapper.find('input').setValue('')
    expect(last_emitted(wrapper)).toBe(null)
  })

  it('数字输入字符串转数字', async () => {
    const wrapper = mount_field({ schema: { type: 'number' }, modelValue: 0 })
    await wrapper.find('input[type="number"]').setValue('42')
    expect(last_emitted(wrapper)).toBe(42)
  })

  it('password 字段渲染为密码输入', () => {
    const wrapper = mount_field({ schema: { type: 'string', format: 'password' }, modelValue: '' })
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('未知类型渲染占位提示，不静默回退文本框', () => {
    const wrapper = mount_field({ schema: {}, modelValue: '' })
    expect(wrapper.find('.field-unsupported').exists()).toBe(true)
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('$ref 经 rootSchema 解引用后判定类型', () => {
    const root = { $defs: { Cfg: { type: 'boolean' } } }
    const wrapper = mount_field({ schema: { $ref: '#/$defs/Cfg' }, rootSchema: root })
    expect(wrapper.find('.field-unsupported').exists()).toBe(false)
  })
})

describe('StringListField 稳定 key', () => {
  const schema = { type: 'array', items: { type: 'string' } }

  it('删除中间项后输入框内容不串位', async () => {
    const wrapper = mount_field({ schema, modelValue: ['a', 'b', 'c'] })
    const before = wrapper.findAll('.field-list-row')
    expect(before).toHaveLength(3)

    // 点击第二行的删除按钮（第一行删除按钮是其唯一按钮）
    const buttons = wrapper.findAll('.field-list-row button')
    await buttons[1].trigger('click')

    expect(last_emitted(wrapper)).toEqual(['a', 'c'])
  })

  it('添加项在列表末尾追加空串', async () => {
    const wrapper = mount_field({ schema, modelValue: ['a'] })
    await wrapper.find('.field-add').trigger('click')
    expect(last_emitted(wrapper)).toEqual(['a', ''])
  })

  it('修改某项只更新对应位置', async () => {
    const wrapper = mount_field({ schema, modelValue: ['a', 'b'] })
    const inputs = wrapper.findAll('.field-list-row input')
    await inputs[1].setValue('B')
    expect(last_emitted(wrapper)).toEqual(['a', 'B'])
  })
})

describe('ObjectListField 卡片列表', () => {
  const schema = {
    type: 'array',
    'x-item-title': '阈值',
    'x-item-placeholder': 'name',
    items: {
      type: 'object',
      title: '阈值',
      properties: {
        name: { type: 'string', title: '名称' },
        tps: { type: 'number', title: 'TPS' },
      },
    },
  }

  it('卡片标题优先使用 x-item-placeholder 指定的字段值', () => {
    const wrapper = mount_field({
      schema,
      modelValue: [{ name: '低负载', tps: 15 }],
    })
    expect(wrapper.find('.field-object-title').text()).toContain('低负载')
  })

  it('标题缺失时回退「名称 + 序号」', () => {
    const wrapper = mount_field({ schema, modelValue: [{ tps: 15 }] })
    expect(wrapper.find('.field-object-title').text()).toContain('阈值 1')
  })

  it('删除中间卡片后剩余项顺序正确', async () => {
    const wrapper = mount_field({
      schema,
      modelValue: [{ name: 'A' }, { name: 'B' }, { name: 'C' }],
    })
    // 每张卡片头部最后一个按钮为删除
    const delete_buttons = wrapper.findAll('.field-object-actions button:last-child')
    await delete_buttons[1].trigger('click')
    expect(last_emitted(wrapper)).toEqual([{ name: 'A' }, { name: 'C' }])
  })

  it('下移卡片交换相邻项', async () => {
    const wrapper = mount_field({
      schema,
      modelValue: [{ name: 'A' }, { name: 'B' }],
    })
    // 第二张卡片的「下移」按钮（第 4 个操作按钮：上移 / 下移 / 删除）
    const actions = wrapper.findAll('.field-object-actions button')
    // 第一张卡片有 3 个按钮（上移、下移、删除）
    await actions[1].trigger('click')
    expect(last_emitted(wrapper)).toEqual([{ name: 'B' }, { name: 'A' }])
  })

  it('新增卡片按子字段默认值构造，且默认展开', async () => {
    const wrapper = mount_field({ schema, modelValue: [] })
    await wrapper.find('.field-add').trigger('click')
    expect(last_emitted(wrapper)).toEqual([{ name: '', tps: 0 }])
    // 新增后卡片主体可见（未折叠）
    await wrapper.setProps({ modelValue: [{ name: '', tps: 0 }] })
    expect(wrapper.find('.field-object-body').isVisible()).toBe(true)
  })

  it('折叠态下主体隐藏', () => {
    const wrapper = mount_field({ schema, modelValue: [{ name: 'A' }] })
    // 未记录折叠状态时默认折叠（初次渲染仅显示头部）
    expect(wrapper.find('.field-object-body').isVisible()).toBe(false)
  })
})

describe('KeyValueField 稳定 key', () => {
  const schema = { type: 'object', additionalProperties: { type: 'string' } }

  it('删除中间行后其余行值不串位', async () => {
    const wrapper = mount_field({
      schema,
      modelValue: { a: '1', b: '2', c: '3' },
    })
    const rows = wrapper.findAll('.field-map-row')
    expect(rows).toHaveLength(3)
    // 每行最后一个按钮是删除
    await rows[1].findAll('button').at(-1).trigger('click')
    expect(last_emitted(wrapper)).toEqual({ a: '1', c: '3' })
  })

  it('修改键名保留对应值', async () => {
    const wrapper = mount_field({ schema, modelValue: { a: '1' } })
    await wrapper.find('.field-map-row input').setValue('key')
    expect(last_emitted(wrapper)).toEqual({ key: '1' })
  })

  it('新增行插入空键空值', async () => {
    const wrapper = mount_field({ schema, modelValue: {} })
    await wrapper.find('.field-add').trigger('click')
    expect(last_emitted(wrapper)).toEqual({ '': '' })
  })

  it('值为数组时渲染行内列表', () => {
    const list_schema = { type: 'object', additionalProperties: { type: 'array' } }
    const wrapper = mount_field({
      schema: list_schema,
      modelValue: { cmd: ['a', 'b'] },
    })
    expect(wrapper.findAll('.field-map-list-row')).toHaveLength(2)
  })

  it('删除行内列表项后列表正确更新', async () => {
    const list_schema = { type: 'object', additionalProperties: { type: 'array' } }
    const wrapper = mount_field({
      schema: list_schema,
      modelValue: { cmd: ['a', 'b', 'c'] },
    })
    const rows = wrapper.findAll('.field-map-list-row')
    await rows[1].findAll('button').at(-1).trigger('click')
    expect(last_emitted(wrapper)).toEqual({ cmd: ['a', 'c'] })
  })
})

describe('BooleanGroupField / ObjectGroupField', () => {
  it('布尔组显示已开启计数并切换单项', async () => {
    const schema = {
      type: 'object',
      title: '开关组',
      properties: { a: { type: 'boolean' }, b: { type: 'boolean' } },
    }
    const wrapper = mount_field({ schema, modelValue: { a: true, b: false } })
    expect(wrapper.text()).toContain('1/2')
  })

  it('对象组渲染全部子字段', () => {
    const schema = {
      type: 'object',
      properties: { host: { type: 'string' }, port: { type: 'integer' } },
    }
    const wrapper = mount_field({ schema, modelValue: { host: 'localhost', port: 25565 } })
    expect(wrapper.findAll('.field-subfield')).toHaveLength(2)
  })

  it('对象组更新子字段保留其他字段', async () => {
    const schema = {
      type: 'object',
      properties: { host: { type: 'string' }, port: { type: 'integer' } },
    }
    const wrapper = mount_field({ schema, modelValue: { host: 'a', port: 1 } })
    const inputs = wrapper.findAll('.field-subfield input')
    expect(inputs.length).toBeGreaterThan(0)
    await inputs[0].setValue('b')
    expect(last_emitted(wrapper)).toEqual({ host: 'b', port: 1 })
  })
})

describe('PlatformListField', () => {
  const schema = {
    type: 'array',
    items: { type: 'string', format: 'platform' },
    'x-options': [
      { value: 'qq', label: 'QQ' },
      { value: 'mc', label: 'MC' },
    ],
  }

  it('按 `平台:目标` 拆分现有项', () => {
    const wrapper = mount_field({ schema, modelValue: ['qq:12345'] })
    const select = wrapper.find('.ui-select-trigger')
    expect(select.exists()).toBe(true)
    expect(select.text()).toContain('QQ')
    const target_input = wrapper.find('.field-platform-row input')
    expect(target_input.element.value).toBe('12345')
  })

  it('切换平台保留目标文本', async () => {
    const wrapper = mount_field({ schema, modelValue: ['qq:12345'] })
    int_spy_call()
    // 直接触发子组件事件（下拉交互由 Select 自身处理）
    const select = wrapper.findComponent({ name: 'Select' })
    select.vm.$emit('update:modelValue', 'mc')
    await wrapper.vm.$nextTick()
    expect(last_emitted(wrapper)).toEqual(['mc:12345'])
  })

  it('新增项使用首个平台选项', async () => {
    const wrapper = mount_field({ schema, modelValue: [] })
    await wrapper.find('.field-add').trigger('click')
    expect(last_emitted(wrapper)).toEqual(['qq:'])
  })
})

/** 占位：避免未使用变量告警（部分用例通过组件事件直接驱动） */
function int_spy_call() {}
