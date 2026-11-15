/**
 * JSON Schema 表单工具（纯函数）。
 *
 * 后端所有动态表单（Config.toml / .env / 扩展配置）统一输出标准 JSON Schema，
 * 前端也统一按此解释字段语义。本模块是「schema → 控件语义」的唯一判定处，
 * 各表单组件不再自行推断类型。
 */

/**
 * 判定字段使用的控件语义。
 * 取值：boolean / number / text / textarea / password / color / select /
 *       string_list / platform_list / object_list / boolean_group / object_group /
 *       key_value / unsupported
 *
 * 除 `unsupported` 外，每种 kind 都必须在 SchemaField.vue 中有对应控件分支。
 */
export function field_kind(schema, key = '') {
  const resolved = effective_schema(schema)
  if (!resolved) return 'text'
  if (Array.isArray(resolved.enum) && resolved.enum.length > 0) return 'select'
  // 单选项 Literal 经 Pydantic 编译为 const（无 enum）
  if (resolved.const !== undefined) return 'select'

  switch (resolved.type) {
    case 'boolean':
      return 'boolean'
    case 'integer':
    case 'number':
      return 'number'
    case 'array':
      return array_kind(resolved)
    case 'object':
      return object_kind(resolved)
    case 'string':
      return string_kind(resolved, key)
    default:
      // 未知 / 缺失 type：交由 SchemaField 渲染占位提示，不静默回退成文本框
      return 'unsupported'
  }
}

function array_kind(schema) {
  if (schema.items?.$ref) return 'object_list'
  const items = effective_schema(schema.items)
  if (items?.type === 'object') return 'object_list'
  if (items?.format === 'platform') return 'platform_list'
  return 'string_list'
}

function object_kind(schema) {
  const properties = schema.properties || {}
  if (Object.keys(properties).length === 0) {
    return schema.additionalProperties ? 'key_value' : 'unsupported'
  }
  const kinds = Object.entries(properties).map(([key, child]) => field_kind(child, key))
  return kinds.every((kind) => kind === 'boolean') ? 'boolean_group' : 'object_group'
}

function string_kind(schema, key) {
  if (schema.format === 'textarea') return 'textarea'
  if (schema.format === 'color') return 'color'
  if (schema.format === 'password') return 'password'
  // 后端约定之外的兜底：按字段名启发式识别密钥
  return is_secret_key(key) ? 'password' : 'text'
}

/** 是否多行文本：显式 `format: 'textarea'`，或单行文本但默认值较长 / 含换行 */
export function is_multiline(schema) {
  const kind = field_kind(schema)
  if (kind === 'textarea') return true
  if (kind !== 'text') return false
  const sample = String(effective_schema(schema)?.default ?? '')
  return sample.length > 40 || sample.includes('\n')
}

/**
 * 字段行布局档位（**唯一判定处**，SchemaForm 据此加修饰类，不另写宽度判断）。
 *
 * - `inline`：左描述 + 右控件两列（开关 / 输入框 / 下拉）。
 * - `wide`  ：整行纵向（多行文本 / 键值映射 / 折叠组，挤在右栏会过窄）。
 * - `aside` ：右栏独立成块（列表类：对象数组卡片 / 字符列表 / 平台列表），
 *             窄屏整行纵向，宽屏回到右栏并靠右对齐。
 */
export function field_layout(schema, key = '') {
  const kind = field_kind(schema, key)
  if (['object_list', 'string_list', 'platform_list'].includes(kind)) return 'aside'
  if (is_multiline(schema)) return 'wide'
  return ['key_value', 'boolean_group', 'object_group'].includes(kind) ? 'wide' : 'inline'
}

/** 密钥字段名启发式（后端未标注 format 时兜底） */
export function is_secret_key(key) {
  return /key|secret|token|password/i.test(key)
}

/** 解包 anyOf / oneOf（Pydantic 的 Optional[T]），取首个非 null 分支 */
export function effective_schema(schema) {
  if (!schema) return null
  const branches = schema.anyOf || schema.oneOf
  if (!Array.isArray(branches)) return schema
  const non_null = branches.find((branch) => branch && branch.type !== 'null')
  if (!non_null) return schema
  const { anyOf, oneOf, ...rest } = schema
  return { ...rest, ...non_null }
}

/** 解析 `#/$defs/xxx` 引用，无法解析返回 null */
export function resolve_ref(root_schema, ref) {
  const segments = String(ref || '')
    .replace(/^#\//, '')
    .split('/')
  let node = root_schema
  for (const segment of segments) {
    if (node == null) return null
    node = node[decodeURIComponent(segment)]
  }
  return node
}

/** 解引用字段 schema（有 $ref 时返回其指向的定义） */
export function dereference(root_schema, schema) {
  if (schema && schema.$ref) return resolve_ref(root_schema, schema.$ref) || schema
  return schema
}

/**
 * 把 JSON Schema 展开为有序字段描述列表。
 * @param {object} root_schema 根 JSON Schema
 * @param {string[]} [keys] 需要渲染的字段名及其顺序；省略则用 properties 声明顺序
 * @returns {{key: string, schema: object, title: string, description: string}[]}
 */
export function schema_fields(root_schema, keys = null) {
  const properties = root_schema?.properties || {}
  const names = keys ? keys.filter((key) => key in properties) : Object.keys(properties)
  return names.map((key) => ({
    key,
    schema: properties[key],
    title: properties[key].title || key,
    description: properties[key].description || '',
  }))
}

/** 字段默认值（按控件语义给出同构初值） */
export function default_value(schema, key = '') {
  const resolved = effective_schema(schema)
  if (resolved && 'default' in resolved) return clone(resolved.default)
  switch (field_kind(schema, key)) {
    case 'boolean':
      return false
    case 'number':
      return 0
    case 'string_list':
    case 'platform_list':
    case 'object_list':
      return []
    case 'key_value':
      return {}
    case 'boolean_group':
    case 'object_group':
      return Object.fromEntries(
        Object.entries(resolved?.properties || {}).map(([name, child]) => [
          name,
          default_value(child, name),
        ]),
      )
    default:
      return ''
  }
}

/** 按控件语义归一化取值，用于草稿与原值同构比较 */
export function normalize_value(schema, key, value) {
  switch (field_kind(schema, key)) {
    case 'boolean':
      return Boolean(value)
    case 'number':
      return value === '' || value == null ? null : Number(value)
    case 'string_list':
    case 'platform_list':
    case 'object_list':
      return Array.isArray(value) ? value : []
    case 'key_value':
    case 'boolean_group':
    case 'object_group':
      return is_plain_object(value) ? value : {}
    default:
      return value ?? ''
  }
}

/** 按控件语义把界面取值转换为提交值（数字空串转 null） */
export function serialize_value(schema, key, value) {
  if (field_kind(schema, key) === 'number') {
    return value === '' || value == null ? null : Number(value)
  }
  return value
}

/** 枚举选项 → 下拉选项（含单选项的 const 形态） */
export function select_options(schema) {
  const resolved = effective_schema(schema)
  const values = Array.isArray(resolved?.enum)
    ? resolved.enum
    : resolved?.const !== undefined
      ? [resolved.const]
      : []
  return values.map((value) => ({
    value,
    label: String(value),
  }))
}

/** 颜色输入只接受合法 hex，非法值回退黑色预览 */
export function color_value(value) {
  return /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(String(value || '')) ? value : '#000000'
}

/** 数字输入步长：浮点用 any，整数用 1 */
export function number_step(schema) {
  return effective_schema(schema)?.type === 'number' ? 'any' : 1
}

/** 是否为普通对象（非数组、非 null） */
export function is_plain_object(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

/** 深拷贝（仅用于 JSON 兼容数据） */
export function clone(value) {
  return JSON.parse(JSON.stringify(value ?? null))
}
