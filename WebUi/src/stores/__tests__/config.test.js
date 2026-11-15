import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/i18n', () => ({
  current_locale: () => 'zh',
  t_global: (key) => key,
}))

const { createPinia, setActivePinia } = await import('pinia')
const { useConfigStore } = await import('@/stores/config')

/** 后端 Config.toml 的示例值 */
function config_payload() {
  return {
    server: { name: '主服', port: 25565 },
    image: { mode: false, template: 'default' },
  }
}

/** 后端 Schema（字段较少但覆盖分组 / 门控） */
function schema_payload() {
  return {
    schema: {
      type: 'object',
      properties: {
        'server.name': { type: 'string', title: '服务器名称' },
        'server.port': { type: 'integer', title: '端口' },
        'image.mode': { type: 'boolean', title: '图片模式' },
        'image.template': { type: 'string', title: '渲染模板' },
      },
    },
    groups: [
      { id: 'server', name: '服务器', keys: ['server.name', 'server.port'] },
      { id: 'image', name: '图片', keys: ['image.mode', 'image.template'] },
    ],
  }
}

/** 环境变量接口返回体 */
function env_payload() {
  return {
    values: { BOT_TOKEN: 'token-a', LOG_LEVEL: 'INFO' },
    schema: {
      type: 'object',
      properties: {
        BOT_TOKEN: { type: 'string', title: '机器人令牌' },
        LOG_LEVEL: { type: 'string', title: '日志级别' },
      },
    },
    groups: [{ id: 'basic', name: '基础', keys: ['BOT_TOKEN', 'LOG_LEVEL'] }],
  }
}

/** 按路径分发响应的 fetch 桩，记录调用次数便于断言刷新行为 */
function stub_fetch({ config = config_payload(), env = env_payload() } = {}) {
  const calls = []
  global.fetch = vi.fn(async (url) => {
    const path = String(url)
    calls.push(path)
    let data
    if (path.includes('/api/config/schema')) data = schema_payload()
    else if (path.includes('/api/config/env')) data = env
    else if (path.includes('/api/config')) data = config
    else throw new Error(`unexpected request: ${path}`)
    return { ok: true, status: 200, json: async () => ({ code: 0, data }) }
  })
  return calls
}

describe('config store 草稿与变更检测', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('fetch_all 推导出扁平键的变更列表', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_all()
    expect(store.has_changes).toBe(false)

    store.update_field('server.name', '子服')
    expect(store.changes).toEqual([
      { key: 'server.name', label: '服务器名称', old_value: '主服', new_value: '子服' },
    ])
    expect(store.has_changes).toBe(true)
  })

  it('reset_draft 丢弃全部改动并回到服务端值', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_all()
    store.update_field('server.port', 25566)
    store.update_field('image.mode', true)

    store.reset_draft()

    expect(store.has_changes).toBe(false)
    expect(store.draft.server.port).toBe(25565)
    expect(store.draft.image.mode).toBe(false)
  })

  it('保存只提交变更字段（PATCH 深合并，未改字段不出现在请求体）', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_all()
    store.update_field('server.port', 25566)

    await store.save_changes()

    const patch_call = global.fetch.mock.calls.find(([, options]) => options?.method === 'PATCH')
    expect(patch_call).toBeTruthy()
    expect(JSON.parse(patch_call[1].body)).toEqual({ server: { port: 25566 } })
    expect(store.has_changes).toBe(false)
  })

  it('无变更时不发请求', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_all()
    const request_count = global.fetch.mock.calls.length

    await store.save_changes()

    expect(global.fetch.mock.calls.length).toBe(request_count)
  })
})

describe('config store 环境变量草稿', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('env 变更按扁平键比对，默认值参与比较', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_env()

    store.update_env_field('LOG_LEVEL', 'DEBUG')
    expect(store.env_changes).toEqual([
      { key: 'LOG_LEVEL', label: '日志级别', old_value: 'INFO', new_value: 'DEBUG' },
    ])
    expect(store.has_env_changes).toBe(true)

    store.reset_env_draft()
    expect(store.has_env_changes).toBe(false)
  })

  it('preserve_draft 刷新时保留未保存的 env 草稿（语言切换场景）', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_env()
    store.update_env_field('BOT_TOKEN', 'token-b')

    await store.fetch_env({ silent: true, preserve_draft: true })

    expect(store.env_draft.BOT_TOKEN).toBe('token-b')
    expect(store.has_env_changes).toBe(true)
  })

  it('普通刷新会用服务端值覆盖草稿', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_env()
    store.update_env_field('BOT_TOKEN', 'token-b')

    await store.fetch_env()

    expect(store.env_draft.BOT_TOKEN).toBe('token-a')
    expect(store.has_env_changes).toBe(false)
  })

  it('fetch_schema 只更新 schema / 分组，不动草稿', async () => {
    stub_fetch()
    const store = useConfigStore()
    await store.fetch_all()
    store.update_field('server.name', '子服')

    await store.fetch_schema()

    expect(store.schema.properties['server.name'].title).toBe('服务器名称')
    expect(store.draft.server.name).toBe('子服')
    expect(store.has_changes).toBe(true)
  })
})
