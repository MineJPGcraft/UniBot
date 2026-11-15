/**
 * WebSocket 实时事件连接（单例）
 * - 通过 HttpOnly cookie 自动携带 access_token 认证
 * - 30 秒心跳，断线自动重连
 * - 支持按事件类型订阅/取消订阅，事件通过回调分发
 * - 每次连接分配递增 generation：旧 socket 的迟到事件（onopen / onmessage /
 *   onclose / onerror）先比对 generation 与当前 socket，不匹配直接丢弃，
 *   避免旧连接把新连接的 connection_state 与心跳状态改坏。
 */
import { ref } from 'vue'
import { API_BASE, is_authenticated } from '@/utils/http'

const connection_state = ref('disconnected') // disconnected | connecting | connected
const event_listeners = new Map() // event_type -> Set<callback>
const subscribed_events = new Set()

let socket = null
/** 当前有效连接的代号；每次 connect / disconnect 递增，用于丢弃过期 socket 事件 */
let connection_generation = 0
let heartbeat_timer = null
let reconnect_timer = null
let reconnect_delay = 1000
let manual_close = false

function build_url() {
  // 生产模式走同源；开发模式下 Vite 不代理 WebSocket，需直连后端，
  // 地址由 `VITE_WEBSOCKET_HOST` 配置（见 .env.development），未配置时按 8000 端口回退。
  // access_token 通过 HttpOnly cookie 自动随 WebSocket 握手发送
  const is_dev = import.meta.env.DEV
  const dev_host = import.meta.env.VITE_WEBSOCKET_HOST || `${window.location.hostname}:8000`
  const host = is_dev ? dev_host : window.location.host
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${host}${API_BASE}/ws`
}

function send(message) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message))
  }
}

function start_heartbeat() {
  stop_heartbeat()
  heartbeat_timer = setInterval(() => send({ type: 'ping' }), 30000)
}

function stop_heartbeat() {
  if (heartbeat_timer) {
    clearInterval(heartbeat_timer)
    heartbeat_timer = null
  }
}

function schedule_reconnect() {
  if (manual_close || reconnect_timer) return
  reconnect_timer = setTimeout(() => {
    reconnect_timer = null
    connect()
  }, reconnect_delay)
  reconnect_delay = Math.min(reconnect_delay * 2, 15000)
}

function connect() {
  if (!is_authenticated()) return
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  )
    return

  manual_close = false
  connection_generation += 1
  const generation = connection_generation
  connection_state.value = 'connecting'
  const current = new WebSocket(build_url())
  socket = current

  /** 事件是否仍来自当前有效连接（旧 socket 的迟到事件一律丢弃） */
  const is_current = () => generation === connection_generation && socket === current

  current.onopen = () => {
    if (!is_current()) return
    connection_state.value = 'connected'
    reconnect_delay = 1000
    start_heartbeat()
    // 重新订阅之前订阅的事件
    if (subscribed_events.size > 0) {
      send({ type: 'subscribe', events: [...subscribed_events] })
    }
  }

  current.onmessage = (event) => {
    if (!is_current()) return
    let message
    try {
      message = JSON.parse(event.data)
    } catch {
      return
    }
    const listeners = event_listeners.get(message.type)
    if (listeners) {
      for (const callback of listeners) callback(message.data, message)
    }
  }

  current.onclose = () => {
    if (!is_current()) return
    connection_state.value = 'disconnected'
    stop_heartbeat()
    schedule_reconnect()
  }

  current.onerror = () => {
    if (!is_current()) return
    current.close()
  }
}

function disconnect() {
  manual_close = true
  // 递增代号：使旧 socket 可能尚未触发的 onclose / onmessage 全部失效
  connection_generation += 1
  stop_heartbeat()
  if (reconnect_timer) {
    clearTimeout(reconnect_timer)
    reconnect_timer = null
  }
  if (socket) {
    socket.close()
    socket = null
  }
  connection_state.value = 'disconnected'
}

/** 订阅事件，返回取消订阅函数 */
function on_event(event_type, callback, { subscribe = true } = {}) {
  if (!event_listeners.has(event_type)) {
    event_listeners.set(event_type, new Set())
  }
  event_listeners.get(event_type).add(callback)

  // subscribe=false 表示仅监听该类型消息，不向服务端注册订阅
  // （如 log_history 是订阅 log 后由服务端补发的缓存消息）
  if (subscribe && !subscribed_events.has(event_type)) {
    subscribed_events.add(event_type)
    send({ type: 'subscribe', events: [event_type] })
  }

  return () => off_event(event_type, callback)
}

function off_event(event_type, callback) {
  const listeners = event_listeners.get(event_type)
  if (!listeners) return
  listeners.delete(callback)
  if (listeners.size === 0) {
    event_listeners.delete(event_type)
    // 仅当该事件确实订阅过时才向服务端取消订阅
    if (subscribed_events.delete(event_type)) {
      send({ type: 'unsubscribe', events: [event_type] })
    }
  }
}

export function use_websocket() {
  return {
    connection_state,
    connect,
    disconnect,
    on_event,
    off_event,
  }
}
