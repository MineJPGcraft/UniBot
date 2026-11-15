import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import {
  clone,
  color_value,
  default_value,
  dereference,
  effective_schema,
  field_kind,
  field_layout,
  is_multiline,
  number_step,
  resolve_ref,
  schema_fields,
  select_options,
  serialize_value,
} from '@/utils/schema_form'

/** 典型字段 schema 片段（与后端 pydantic 输出形态一致） */
const ROOT = {
  type: 'object',
  $defs: {
    Threshold: {
      type: 'object',
      title: '阈值',
      properties: {
        tps: { type: 'number', title: 'TPS' },
        mspt: { type: 'number', title: 'MSPT' },
      },
    },
  },
  properties: {
    enabled: { type: 'boolean' },
    count: { type: 'integer' },
    ratio: { type: 'number' },
    name: { type: 'string' },
    note: { type: 'string', format: 'textarea' },
    secret: { type: 'string', format: 'password' },
    api_key: { type: 'string' },
    tint: { type: 'string', format: 'color' },
    mode: { enum: ['off', 'on'] },
    literal: { const: 'fixed' },
    optional_mode: { anyOf: [{ type: 'string' }, { type: 'null' }] },
    names: { type: 'array', items: { type: 'string' } },
    platforms: { type: 'array', items: { type: 'string', format: 'platform' } },
    thresholds: { type: 'array', items: { $ref: '#/$defs/Threshold' } },
    inline_objects: {
      type: 'array',
      items: { type: 'object', properties: { value: { type: 'string' } } },
    },
    mapping: { type: 'object', additionalProperties: { type: 'string' } },
    mapping_lists: { type: 'object', additionalProperties: { type: 'array' } },
    switches: { type: 'object', properties: { a: { type: 'boolean' }, b: { type: 'boolean' } } },
    nested: { type: 'object', properties: { a: { type: 'string' } } },
    unknown: {},
  },
}

describe('field_kind', () => {
  it('识别基础标量类型', () => {
    expect(field_kind(ROOT.properties.enabled)).toBe('boolean')
    expect(field_kind(ROOT.properties.count)).toBe('number')
    expect(field_kind(ROOT.properties.ratio)).toBe('number')
    expect(field_kind(ROOT.properties.name)).toBe('text')
  })

  it('识别字符串格式（textarea / password / color）', () => {
    expect(field_kind(ROOT.properties.note)).toBe('textarea')
    expect(field_kind(ROOT.properties.secret)).toBe('password')
    expect(field_kind(ROOT.properties.tint)).toBe('color')
  })

  it('密钥字段名启发式识别为密码框', () => {
    expect(field_kind(ROOT.properties.api_key, 'api_key')).toBe('password')
  })

  it('enum 与 const 均识别为下拉选择', () => {
    expect(field_kind(ROOT.properties.mode)).toBe('select')
    expect(field_kind(ROOT.properties.literal)).toBe('select')
  })

  it('anyOf 可选类型解包后识别', () => {
    expect(field_kind(ROOT.properties.optional_mode)).toBe('text')
  })

  it('识别列表类（字符串 / 平台 / 对象数组）', () => {
    expect(field_kind(ROOT.properties.names)).toBe('string_list')
    expect(field_kind(ROOT.properties.platforms)).toBe('platform_list')
    expect(field_kind(ROOT.properties.thresholds)).toBe('object_list')
    expect(field_kind(ROOT.properties.inline_objects)).toBe('object_list')
  })

  it('识别对象类（键值映射 / 布尔组 / 对象组）', () => {
    expect(field_kind(ROOT.properties.mapping)).toBe('key_value')
    expect(field_kind(ROOT.properties.mapping_lists)).toBe('key_value')
    expect(field_kind(ROOT.properties.switches)).toBe('boolean_group')
    expect(field_kind(ROOT.properties.nested)).toBe('object_group')
  })

  it('未知类型返回 unsupported（不静默回退成文本框）', () => {
    expect(field_kind(ROOT.properties.unknown)).toBe('unsupported')
  })
})

describe('field_layout', () => {
  it('列表类走 aside 档位', () => {
    expect(field_layout(ROOT.properties.names)).toBe('aside')
    expect(field_layout(ROOT.properties.platforms)).toBe('aside')
    expect(field_layout(ROOT.properties.thresholds)).toBe('aside')
  })

  it('多行文本与映射类走 wide 档位', () => {
    expect(field_layout(ROOT.properties.note)).toBe('wide')
    expect(field_layout(ROOT.properties.mapping)).toBe('wide')
    expect(field_layout(ROOT.properties.switches)).toBe('wide')
    expect(field_layout(ROOT.properties.nested)).toBe('wide')
  })

  it('普通输入走 inline 档位', () => {
    expect(field_layout(ROOT.properties.name)).toBe('inline')
    expect(field_layout(ROOT.properties.enabled)).toBe('inline')
  })
})

describe('is_multiline', () => {
  it('显式 textarea 为多行', () => {
    expect(is_multiline(ROOT.properties.note)).toBe(true)
  })

  it('长默认值的单行文本按多行处理', () => {
    expect(is_multiline({ type: 'string', default: 'x'.repeat(41) })).toBe(true)
    expect(is_multiline({ type: 'string', default: 'x'.repeat(10) })).toBe(false)
  })

  it('非文本类型不为多行', () => {
    expect(is_multiline(ROOT.properties.enabled)).toBe(false)
  })
})

describe('effective_schema / resolve_ref / dereference', () => {
  it('解包 anyOf 并保留外层元信息', () => {
    const resolved = effective_schema({
      title: '可选',
      anyOf: [{ type: 'null' }, { type: 'string', format: 'password' }],
    })
    expect(resolved.type).toBe('string')
    expect(resolved.format).toBe('password')
    expect(resolved.title).toBe('可选')
  })

  it('无 anyOf 时原样返回', () => {
    const schema = { type: 'string' }
    expect(effective_schema(schema)).toBe(schema)
    expect(effective_schema(null)).toBe(null)
  })

  it('解析 #/$defs 引用', () => {
    expect(resolve_ref(ROOT, '#/$defs/Threshold')).toBe(ROOT.$defs.Threshold)
    expect(resolve_ref(ROOT, '#/$defs/Missing')).toBe(undefined)
  })

  it('dereference 解引用字段 schema', () => {
    const schema = { $ref: '#/$defs/Threshold' }
    expect(dereference(ROOT, schema)).toBe(ROOT.$defs.Threshold)
  })

  it('无法解析的引用原样返回，不抛错', () => {
    const schema = { $ref: '#/$defs/Missing' }
    expect(dereference(ROOT, schema)).toEqual({ $ref: '#/$defs/Missing' })
  })
})

describe('schema_fields', () => {
  it('按声明顺序展开字段描述', () => {
    const fields = schema_fields({ properties: { a: { title: 'A' }, b: {} } })
    expect(fields.map((field) => field.key)).toEqual(['a', 'b'])
    expect(fields[0].title).toBe('A')
    // 无 title 时回退字段名
    expect(fields[1].title).toBe('b')
  })

  it('传入 keys 时按其顺序且过滤不存在的字段', () => {
    const fields = schema_fields({ properties: { a: {}, b: {} } }, ['b', 'missing', 'a'])
    expect(fields.map((field) => field.key)).toEqual(['b', 'a'])
  })
})

describe('default_value', () => {
  it('优先使用 schema 声明的默认值', () => {
    expect(default_value({ type: 'number', default: 5 })).toBe(5)
    expect(default_value({ type: 'string', default: 'x' })).toBe('x')
  })

  it('按控件语义给出同构初值', () => {
    expect(default_value({ type: 'boolean' })).toBe(false)
    expect(default_value({ type: 'integer' })).toBe(0)
    expect(default_value({ type: 'array', items: { type: 'string' } })).toEqual([])
    expect(default_value({ type: 'object', additionalProperties: {} })).toEqual({})
    expect(default_value({ type: 'string' })).toBe('')
  })

  it('对象组的默认值递归填充子字段', () => {
    expect(default_value(ROOT.properties.switches)).toEqual({ a: false, b: false })
  })

  it('默认值返回深拷贝，修改不影响 schema', () => {
    const schema = { type: 'array', default: [1] }
    const value = default_value(schema)
    value.push(2)
    expect(schema.default).toEqual([1])
  })
})

describe('serialize_value', () => {
  it('数字字段空值序列化为 null', () => {
    expect(serialize_value({ type: 'number' }, 'count', '')).toBe(null)
    expect(serialize_value({ type: 'number' }, 'count', null)).toBe(null)
  })

  it('数字字段字符串转数字', () => {
    expect(serialize_value({ type: 'number' }, 'count', '42')).toBe(42)
  })

  it('其余类型原样返回', () => {
    expect(serialize_value({ type: 'string' }, 'name', 'abc')).toBe('abc')
  })
})

describe('select_options', () => {
  it('enum 展开为 value/label 选项', () => {
    expect(select_options({ enum: ['a', 'b'] })).toEqual([
      { value: 'a', label: 'a' },
      { value: 'b', label: 'b' },
    ])
  })

  it('const 单选项转单元素数组', () => {
    expect(select_options({ const: 'fixed' })).toEqual([{ value: 'fixed', label: 'fixed' }])
  })

  it('无 enum / const 时返回空数组', () => {
    expect(select_options({ type: 'string' })).toEqual([])
  })
})

describe('color_value / number_step / clone', () => {
  it('颜色非法值回退黑色，支持 6 位与 8 位 hex', () => {
    expect(color_value('#ff0000')).toBe('#ff0000')
    expect(color_value('#ff000080')).toBe('#ff000080')
    expect(color_value('red')).toBe('#000000')
    expect(color_value('')).toBe('#000000')
  })

  it('浮点步长为 any，整数为 1', () => {
    expect(number_step({ type: 'number' })).toBe('any')
    expect(number_step({ type: 'integer' })).toBe(1)
  })

  it('clone 深拷贝 JSON 数据', () => {
    const source = { a: [1, 2] }
    const copy = clone(source)
    copy.a.push(3)
    expect(source.a).toEqual([1, 2])
  })

  it('clone 对 null 返回 null', () => {
    expect(clone(null)).toBe(null)
  })
})

// 保证测试文件里 import 的 ref 不产生未使用告警（辅助断言）
void ref
