/**
 * 任务中心 Store：后台任务列表 + 详情 + WebSocket 实时进度
 *
 * 状态判定与文案映射统一放在 `utils/task.js`（纯函数，供组件与 store 共用），
 * 本 store 只负责数据获取、缓存合并与实时订阅。
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'
import { ACTIVE_STATUSES } from '@/utils/task'
import { use_websocket } from '@/composables/use_websocket'

/** 保留的任务条数上限（与后端 MAX_HISTORY 对齐，避免列表无限增长） */
const MAX_TASKS = 50

/** 等待任务结束的轮询间隔与总超时（毫秒） */
const TASK_POLL_INTERVAL_MS = 2000
const TASK_WAIT_TIMEOUT_MS = 180000

export const useTaskStore = defineStore('task', () => {
  const items = ref([])
  const summary = ref({ pending: 0, running: 0 })
  const selected_id = ref('')
  const logs = ref([])
  const loading = ref(false)
  let unsubscribe = null

  const active_count = computed(() => (summary.value.pending || 0) + (summary.value.running || 0))

  const has_active = computed(() => active_count.value > 0)

  const selected = computed(() => items.value.find((item) => item.id === selected_id.value) || null)

  /** 按创建时间倒序排列的任务列表（后端已倒序，此处防御性排序） */
  const sorted_items = computed(() =>
    [...items.value].sort((left, right) => (right.created_at || 0) - (left.created_at || 0)),
  )

  function merge_task(task) {
    const index = items.value.findIndex((item) => item.id === task.id)
    if (index === -1) {
      items.value = [task, ...items.value].slice(0, MAX_TASKS)
      return
    }
    items.value[index] = { ...items.value[index], ...task }
  }

  function recompute_summary() {
    const next = { pending: 0, running: 0 }
    for (const task of items.value) {
      if (task.status === 'pending') next.pending += 1
      else if (task.status === 'running') next.running += 1
    }
    summary.value = next
  }

  async function fetch_tasks() {
    loading.value = true
    try {
      const data = await http.get('/api/tasks')
      items.value = data?.items || []
      summary.value = data?.summary || { pending: 0, running: 0 }
    } finally {
      loading.value = false
    }
    return items.value
  }

  async function fetch_task(task_id) {
    const task = await http.get(`/api/tasks/${encodeURIComponent(task_id)}`)
    merge_task(task)
    recompute_summary()
    return task
  }

  /** 拉取任务日志（详情抽屉打开 / 任务更新时调用） */
  async function fetch_logs(task_id) {
    const task = await http.get(`/api/tasks/${encodeURIComponent(task_id)}`)
    merge_task(task)
    recompute_summary()
    logs.value = task?.logs || []
    return logs.value
  }

  async function cancel_task(task_id) {
    const data = await http.post(`/api/tasks/${encodeURIComponent(task_id)}/cancel`)
    await fetch_tasks()
    if (selected_id.value === task_id) await fetch_logs(task_id)
    return data
  }

  async function retry_task(task_id) {
    const data = await http.post(`/api/tasks/${encodeURIComponent(task_id)}/retry`)
    await fetch_tasks()
    if (selected_id.value === task_id) await fetch_logs(task_id)
    return data
  }

  /** 手动触发依赖同步（uv add / uv remove / uv sync） */
  async function sync_dependencies() {
    const task = await http.post('/api/tasks/dependency-sync')
    merge_task(task)
    recompute_summary()
    return task
  }

  /**
   * 轮询等待任务结束并返回最终快照。
   *
   * 供需要「任务结果」的调用方使用（如 Studio 启动后要拿 result.url）；
   * 无结果的调用方（市场安装等）直接刷新列表即可，不必等待。
   */
  async function wait_task(task_id, { timeout_ms: timeout_ms = TASK_WAIT_TIMEOUT_MS } = {}) {
    const deadline = Date.now() + timeout_ms
    let task = await fetch_task(task_id)
    while (task && ACTIVE_STATUSES.has(task.status)) {
      if (Date.now() > deadline) return task
      await new Promise((resolve) => setTimeout(resolve, TASK_POLL_INTERVAL_MS))
      task = await fetch_task(task_id)
    }
    return task
  }

  function select(task_id) {
    selected_id.value = task_id
    if (task_id) fetch_logs(task_id)
  }

  function clear_selection() {
    selected_id.value = ''
    logs.value = []
  }

  /** 订阅 WebSocket 的 task 事件推送（断线重连后自动恢复订阅） */
  function init() {
    if (unsubscribe) return
    const { on_event } = use_websocket()
    unsubscribe = on_event('task', (data) => {
      if (!data?.id) return
      merge_task(data)
      recompute_summary()
      if (data.id === selected_id.value) fetch_logs(data.id)
    })
  }

  function dispose() {
    unsubscribe?.()
    unsubscribe = null
  }

  function reset() {
    items.value = []
    summary.value = { pending: 0, running: 0 }
    clear_selection()
  }

  return {
    items,
    summary,
    selected_id,
    logs,
    loading,
    active_count,
    has_active,
    selected,
    sorted_items,
    fetch_tasks,
    fetch_task,
    fetch_logs,
    cancel_task,
    retry_task,
    sync_dependencies,
    wait_task,
    select,
    clear_selection,
    init,
    dispose,
    reset,
  }
})
