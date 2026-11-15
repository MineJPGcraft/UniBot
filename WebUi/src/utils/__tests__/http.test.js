import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/i18n', () => ({
  current_locale: () => 'zh',
  t_global: (key) => key,
}))

const { ApiError, http, api_url, is_authenticated, API_BASE } = await import('@/utils/http')

/** 构造一个可编程的 fetch 响应 */
function json_response(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

/** 依次返回给定响应的 fetch 桩，并记录调用 */
function stub_fetch(responses) {
  const calls = []
  global.fetch = vi.fn(async (url, options = {}) => {
    calls.push({ url: String(url), options })
    const next = responses.shift()
    if (!next) throw new Error('fetch called more times than expected')
    return typeof next === 'function' ? next(url, options) : next
  })
  return calls
}

describe('api_url / API_BASE', () => {
  it('统一拼接后端前缀', () => {
    expect(API_BASE).toBe('/webui')
    expect(api_url('/api/tasks')).toBe('/webui/api/tasks')
  })
})

describe('is_authenticated', () => {
  beforeEach(() => {
    document.cookie = 'unibot_authenticated=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  })

  it('无标记 cookie 时未登录', () => {
    expect(is_authenticated()).toBe(false)
  })

  it('存在标记 cookie 时视为已登录', () => {
    document.cookie = 'unibot_authenticated=1; path=/'
    expect(is_authenticated()).toBe(true)
  })
})

describe('http 请求', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('成功请求返回 result.data', async () => {
    stub_fetch([json_response({ code: 0, data: { value: 1 } })])
    await expect(http.get('/api/demo')).resolves.toEqual({ value: 1 })
  })

  it('业务错误（code !== 0）抛 ApiError 并携带 code / message', async () => {
    stub_fetch([json_response({ code: 7, message: '坏了' })])
    await expect(http.get('/api/demo')).rejects.toMatchObject({
      name: 'ApiError',
      code: 7,
      message: '坏了',
    })
  })

  it('协议错误（404）解析 detail 作为提示', async () => {
    stub_fetch([json_response({ detail: '没找到' }, 404)])
    await expect(http.get('/api/demo')).rejects.toMatchObject({ code: 404, message: '没找到' })
  })

  it('请求携带 Accept-Language 与 cookie 凭证', async () => {
    const calls = stub_fetch([json_response({ code: 0, data: null })])
    await http.get('/api/demo')
    expect(calls[0].options.credentials).toBe('include')
    expect(calls[0].options.headers['Accept-Language']).toBe('zh')
  })

  it('GET 不发送 Content-Type，POST 才发送', async () => {
    const calls = stub_fetch([
      json_response({ code: 0, data: null }),
      json_response({ code: 0, data: null }),
    ])
    await http.get('/api/demo')
    await http.post('/api/demo', { a: 1 })
    expect(calls[0].options.headers['Content-Type']).toBeUndefined()
    expect(calls[1].options.headers['Content-Type']).toBe('application/json')
  })

  it('查询参数拼接进 URL，空值被忽略', async () => {
    const calls = stub_fetch([json_response({ code: 0, data: null })])
    await http.get('/api/demo', { query: { page: 2, empty: '', missing: null } })
    expect(calls[0].url).toContain('page=2')
    expect(calls[0].url).not.toContain('empty')
    expect(calls[0].url).not.toContain('missing')
  })
})

describe('401 单飞刷新', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.dispatchEvent = vi.fn()
  })

  it('401 时刷新成功后自动重试原请求', async () => {
    stub_fetch([
      json_response({ detail: 'expired' }, 401),
      json_response({ code: 0, data: null }), // refresh
      json_response({ code: 0, data: { retried: true } }), // retry
    ])
    await expect(http.get('/api/demo')).resolves.toEqual({ retried: true })
  })

  it('并发 401 只发起一次刷新（单飞）', async () => {
    let refresh_calls = 0
    const calls = stub_fetch([
      json_response({ detail: 'expired' }, 401),
      json_response({ detail: 'expired' }, 401),
      () => {
        refresh_calls += 1
        return json_response({ code: 0 })
      },
      json_response({ code: 0, data: 'a' }),
      json_response({ code: 0, data: 'b' }),
    ])
    const [first, second] = await Promise.all([http.get('/api/one'), http.get('/api/two')])
    expect(refresh_calls).toBe(1)
    expect([first, second]).toEqual(['a', 'b'])
    expect(calls.filter((call) => call.url.includes('/auth/refresh'))).toHaveLength(1)
  })

  it('刷新失败时派发 unibot:unauthorized 并抛出错误', async () => {
    const dispatched = []
    window.dispatchEvent = (event) => dispatched.push(event.type)
    stub_fetch([
      json_response({ detail: 'expired' }, 401),
      json_response({ detail: 'refresh failed' }, 401),
    ])
    await expect(http.get('/api/demo')).rejects.toBeInstanceOf(ApiError)
    expect(dispatched).toContain('unibot:unauthorized')
  })

  it('登录 / 初始化接口不触发刷新（避免递归）', async () => {
    const calls = stub_fetch([json_response({ detail: 'bad credentials' }, 401)])
    await expect(http.post('/api/auth/login', {})).rejects.toMatchObject({ code: 401 })
    expect(calls).toHaveLength(1)
  })

  it('刷新后仍 401 则派发未授权事件', async () => {
    const dispatched = []
    window.dispatchEvent = (event) => dispatched.push(event.type)
    stub_fetch([
      json_response({ detail: 'expired' }, 401),
      json_response({ code: 0 }), // refresh 成功
      json_response({ detail: 'expired' }, 401), // 重试仍 401
    ])
    await expect(http.get('/api/demo')).rejects.toMatchObject({ code: 401 })
    expect(dispatched).toContain('unibot:unauthorized')
  })
})

describe('网络异常', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('超时错误转换为可读提示', async () => {
    global.fetch = vi.fn(async () => {
      const error = new Error('timeout')
      error.name = 'TimeoutError'
      throw error
    })
    await expect(http.get('/api/demo')).rejects.toMatchObject({
      code: 0,
      message: 'common.request_timeout',
    })
  })

  it('断网转换为网络错误提示', async () => {
    global.fetch = vi.fn(async () => {
      throw new Error('offline')
    })
    await expect(http.get('/api/demo')).rejects.toMatchObject({
      code: 0,
      message: 'common.network_error',
    })
  })

  it('非 JSON 响应体回退状态码提示', async () => {
    stub_fetch([
      {
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('not json')
        },
      },
    ])
    await expect(http.get('/api/demo')).rejects.toBeInstanceOf(ApiError)
  })
})
