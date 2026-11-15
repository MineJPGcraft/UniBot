import { current_locale, t_global } from '@/i18n'

/**
 * HTTP 请求封装
 * - JWT 通过 HttpOnly cookie 自动携带（无需手动管理 token）
 * - access_token 过期（401）时自动用 refresh_token 刷新并重试
 * - 统一解析 { code, data, message } 响应格式
 * - 协议级错误（400/401/403/404）由 HTTP 状态码承载，解析 detail 提示
 */

/** 后端挂载前缀（SSE/WebSocket/静态头像等场景统一引用） */
export const API_BASE = '/webui'

/** 请求默认超时（毫秒） */
const DEFAULT_TIMEOUT_MS = 15000

/** 标记 cookie key（非 HttpOnly，仅用于前端快速判断登录态） */
const AUTH_FLAG_KEY = 'unibot_authenticated'

/** 拼接后端 URL（供 fetch 以外的场景复用，如 EventSource / WebSocket） */
export function api_url(path) {
  return `${API_BASE}${path}`
}

/** 检查是否存在登录标记 cookie */
export function is_authenticated() {
  return document.cookie.split('; ').some((row) => row.startsWith(AUTH_FLAG_KEY + '='))
}

/** 业务错误：code !== 0 或 HTTP 非 2xx 时抛出，携带 code 与 message */
export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

let refresh_promise = null

/** 不依赖登录态的接口：401 时直接失败，不触发刷新重试（其余接口过期时均应刷新后重试） */
const NO_REFRESH_PATHS = new Set(['/api/auth/login', '/api/auth/setup'])

async function refresh_access_token() {
  // refresh_token 在 HttpOnly cookie 中，由后端自动读取；失效时后端返回 401
  let response
  try {
    response = await fetch(api_url('/api/auth/refresh'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept-Language': current_locale() },
      credentials: 'include',
      body: '{}',
      signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
    })
  } catch {
    throw new ApiError(0, t_global('common.network_error'))
  }
  if (!response.ok) throw new ApiError(response.status, t_global('common.session_expired'))
  const result = await response.json()
  if (result.code !== 0)
    throw new ApiError(result.code, result.message || t_global('common.refresh_failed'))
}

/** 把非 2xx 响应转换为携带 detail 的 ApiError（FastAPI HTTPException 返回 { detail }） */
async function problem_to_error(response) {
  let detail = `${t_global('common.request_failed')}: ${response.status}`
  try {
    const problem = await response.json()
    detail = problem.detail || problem.message || detail
  } catch {
    // 非 JSON 响应体，保留默认提示
  }
  return new ApiError(response.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
}

/** 包装网络层异常（断网 / 超时）为可读的 ApiError */
async function do_fetch(url, options) {
  try {
    return await fetch(url, options)
  } catch (error) {
    if (error.name === 'TimeoutError') throw new ApiError(0, t_global('common.request_timeout'))
    throw new ApiError(0, t_global('common.network_error'))
  }
}

async function request(
  method,
  path,
  { body, query, auth = true, timeout_ms: timeout_ms = DEFAULT_TIMEOUT_MS } = {},
) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, value)
      }
    }
  }

  const send = () =>
    do_fetch(url, {
      method,
      // 无请求体的方法不发送 Content-Type
      headers:
        body !== undefined
          ? { 'Content-Type': 'application/json', 'Accept-Language': current_locale() }
          : { 'Accept-Language': current_locale() },
      credentials: 'include',
      signal: AbortSignal.timeout(timeout_ms),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })

  let response = await send()

  // access_token 过期：尝试刷新一次后重试（登录/初始化等无登录态接口除外，
  // /api/auth/me 等认证接口过期时同样需要刷新，否则页面加载后拿不到用户权限）
  if (response.status === 401 && auth && !NO_REFRESH_PATHS.has(path)) {
    try {
      refresh_promise = refresh_promise || refresh_access_token()
      await refresh_promise
      refresh_promise = null
      response = await send()
    } catch (error) {
      refresh_promise = null
      window.dispatchEvent(new CustomEvent('unibot:unauthorized'))
      throw error
    }
  }

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('unibot:unauthorized'))
    throw new ApiError(401, t_global('common.session_expired'))
  }

  // 其余协议级错误（400/403/404…）：解析 detail 作为提示
  if (!response.ok) throw await problem_to_error(response)

  let result
  try {
    result = await response.json()
  } catch {
    throw new ApiError(response.status, `${t_global('common.request_failed')}: ${response.status}`)
  }

  if (result.code !== 0) {
    throw new ApiError(result.code, result.message || t_global('common.request_failed'))
  }
  return result.data
}

export const http = {
  get: (path, options) => request('GET', path, options),
  post: (path, body, options) => request('POST', path, { ...options, body }),
  put: (path, body, options) => request('PUT', path, { ...options, body }),
  patch: (path, body, options) => request('PATCH', path, { ...options, body }),
  delete: (path, options) => request('DELETE', path, options),
}
