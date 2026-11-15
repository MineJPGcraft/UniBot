import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/http', () => ({
  API_BASE: '/webui',
  is_authenticated: () => true,
}))

/** 可手动触发事件的 WebSocket 桩 */
class FakeSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = FakeSocket.CONNECTING
    this.sent = []
    this.closed = false
    FakeSocket.instances.push(this)
  }

  send(payload) {
    this.sent.push(JSON.parse(payload))
  }

  close() {
    this.closed = true
    this.readyState = FakeSocket.CLOSED
  }

  /** 模拟连接建立 */
  open() {
    this.readyState = FakeSocket.OPEN
    this.onopen?.()
  }

  /** 模拟服务端推送 */
  message(data) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  /** 模拟连接关闭 */
  server_close() {
    this.readyState = FakeSocket.CLOSED
    this.onclose?.()
  }
}

global.WebSocket = FakeSocket

// 单例模块：整组用例共用，注意每个用例先 disconnect 复位
const { use_websocket } = await import('@/composables/use_websocket')

describe('use_websocket 连接代号（generation）', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeSocket.instances.length = 0
  })

  it('连接后状态为 connected，断线后变回 disconnected', () => {
    const { connect, disconnect, connection_state } = use_websocket()
    disconnect()
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    expect(connection_state.value).toBe('connected')
    socket.server_close()
    expect(connection_state.value).toBe('disconnected')
    disconnect()
  })

  it('旧 socket 的迟到 onclose 不会把新连接状态改坏', () => {
    const { connect, disconnect, connection_state } = use_websocket()
    disconnect()
    connect()
    const stale = FakeSocket.instances.at(-1)
    stale.open()

    // 强制建立新连接（模拟重连）：旧 socket 被替换
    disconnect()
    connect()
    const fresh = FakeSocket.instances.at(-1)
    fresh.open()
    expect(connection_state.value).toBe('connected')

    // 旧 socket 此时才触发 onclose（迟到事件）
    stale.onclose?.()
    expect(connection_state.value).toBe('connected')

    // 旧 socket 的迟到消息不应分发给监听者
    let received = 0
    const { on_event } = use_websocket()
    const off = on_event('demo', () => {
      received += 1
    })
    stale.onmessage?.({ data: JSON.stringify({ type: 'demo' }) })
    expect(received).toBe(0)
    fresh.message({ type: 'demo' })
    expect(received).toBe(1)
    off()
    disconnect()
  })

  it('disconnect 后旧 socket 的迟到事件被忽略', () => {
    const { connect, disconnect, connection_state } = use_websocket()
    disconnect()
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    disconnect()
    expect(connection_state.value).toBe('disconnected')

    socket.onopen?.()
    expect(connection_state.value).toBe('disconnected')
    socket.onclose?.()
    expect(connection_state.value).toBe('disconnected')
  })

  it('连接建立后按已订阅集合重新订阅', () => {
    const { connect, disconnect, on_event } = use_websocket()
    disconnect()
    const off = on_event('log', () => {})
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    const subscribe = socket.sent.find((message) => message.type === 'subscribe')
    expect(subscribe.events).toContain('log')
    off()
    disconnect()
  })

  it('subscribe=false 仅本地监听，不向服务端订阅', () => {
    const { connect, disconnect, on_event } = use_websocket()
    disconnect()
    const off = on_event('log_history', () => {}, { subscribe: false })
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    expect(socket.sent.some((message) => message.type === 'subscribe')).toBe(false)
    off()
    disconnect()
  })

  it('连接期间订阅新事件会立即发订阅消息', () => {
    const { connect, disconnect, on_event } = use_websocket()
    disconnect()
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    const off = on_event('player', () => {})
    expect(socket.sent.at(-1)).toEqual({ type: 'subscribe', events: ['player'] })
    // 取消最后一个监听者时同步退订
    off()
    expect(socket.sent.at(-1)).toEqual({ type: 'unsubscribe', events: ['player'] })
    disconnect()
  })

  it('心跳按 30s 间隔发送 ping', () => {
    const { connect, disconnect } = use_websocket()
    disconnect()
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    vi.advanceTimersByTime(30000)
    expect(socket.sent.filter((message) => message.type === 'ping')).toHaveLength(1)
    vi.advanceTimersByTime(30000)
    expect(socket.sent.filter((message) => message.type === 'ping')).toHaveLength(2)
    disconnect()
  })

  it('断线后按退避策略自动重连', () => {
    const { connect, disconnect } = use_websocket()
    disconnect()
    connect()
    const first = FakeSocket.instances.at(-1)
    first.open()
    first.server_close()
    expect(FakeSocket.instances).toHaveLength(1)
    vi.advanceTimersByTime(1000)
    expect(FakeSocket.instances).toHaveLength(2)
    disconnect()
  })

  it('手动断开后不再自动重连', () => {
    const { connect, disconnect } = use_websocket()
    disconnect()
    connect()
    const socket = FakeSocket.instances.at(-1)
    socket.open()
    disconnect()
    vi.advanceTimersByTime(60000)
    expect(FakeSocket.instances).toHaveLength(1)
  })
})

describe('use_websocket 连接地址构造', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeSocket.instances.length = 0
  })

  afterEach(() => {
    use_websocket().disconnect()
    vi.useRealTimers()
  })

  it('开发模式下使用 VITE_WEBSOCKET_HOST 配置的地址', () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_WEBSOCKET_HOST', '192.168.1.10:9000')
    const { connect } = use_websocket()
    connect()
    expect(FakeSocket.instances.at(-1).url).toBe('ws://192.168.1.10:9000/webui/ws')
    vi.unstubAllEnvs()
  })

  it('开发模式未配置时回退到当前主机 8000 端口', () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_WEBSOCKET_HOST', '')
    const { connect } = use_websocket()
    connect()
    expect(FakeSocket.instances.at(-1).url).toBe(`ws://${window.location.hostname}:8000/webui/ws`)
    vi.unstubAllEnvs()
  })

  it('生产模式使用同源地址', () => {
    vi.stubEnv('DEV', false)
    vi.stubEnv('VITE_WEBSOCKET_HOST', 'ignored:9999')
    const { connect } = use_websocket()
    connect()
    expect(FakeSocket.instances.at(-1).url).toBe(`ws://${window.location.host}/webui/ws`)
    vi.unstubAllEnvs()
  })
})
