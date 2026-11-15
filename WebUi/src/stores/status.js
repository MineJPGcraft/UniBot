/**
 * 系统状态 Store：运行概览 + WebSocket 实时推送
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'
import { use_websocket } from '@/composables/use_websocket'

export const useStatusStore = defineStore('status', () => {
  const status = ref(null)
  const loading = ref(false)
  let unsubscribe = null

  async function fetch_status() {
    loading.value = true
    try {
      status.value = await http.get('/api/status')
    } finally {
      loading.value = false
    }
    return status.value
  }

  async function check_update() {
    // 后端访问 GitHub API，放宽超时
    const data = await http.post('/api/status/check-update', {}, { timeout_ms: 30000 })
    status.value = { ...status.value, ...data }
    return data
  }

  /**
   * 从 GitHub Release 更新机器人（提交任务中心任务，下载完成后由后端触发重启）。
   * 进度在任务中心查看。
   */
  async function update_bot() {
    return await http.post('/api/status/update')
  }

  /** 获取当前认证令牌（用于快速授权初始化） */
  async function fetch_token() {
    const data = await http.get('/api/status/token')
    return data?.token ?? ''
  }

  /** 订阅 WebSocket 的 status 事件推送（断线重连后自动恢复订阅） */
  function init() {
    if (unsubscribe) return
    const { on_event } = use_websocket()
    unsubscribe = on_event('status', (data) => {
      status.value = data
    })
  }

  function dispose() {
    unsubscribe?.()
    unsubscribe = null
  }

  return { status, loading, fetch_status, check_update, update_bot, fetch_token, init, dispose }
})
