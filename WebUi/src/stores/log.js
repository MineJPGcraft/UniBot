/**
 * 日志 Store：文件列表 + 内容分页过滤
 * 正则解析文件日志格式（Scripts/Logging.py file_format）：
 *   MM-DD HH:mm:ss [LEVEL] module | message
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'
import { use_websocket } from '@/composables/use_websocket'

const LOG_LINE_PATTERN =
  /^(?<date>\d{2}-\d{2})\s+(?<time>\d{2}:\d{2}:\d{2})\s*\[(?<level>\w+)\]\s*(?<module>[^|]+?)\s*\|\s*(?<message>.*)$/

/** 实时日志缓存上限（跨页面共享，超出后丢弃最早的） */
const MAX_LIVE_LOGS = 500

/** 首页展示的最近日志条数（倒序缓存，避免每次推送重建数组） */
const MAX_RECENT_LOGS = 80

function parse_line(raw) {
  const match = raw.text.match(LOG_LINE_PATTERN)
  if (match) {
    return {
      line: raw.line,
      // 只保留到分钟（HH:mm），省略日期与秒，便于各列对齐
      time: match.groups.time.slice(0, 5),
      level: match.groups.level,
      module: match.groups.module.trim(),
      message: match.groups.message,
    }
  }
  return { line: raw.line, time: '', level: '', module: '', message: raw.text }
}

export const useLogStore = defineStore('log', () => {
  const file_list = ref([])
  const current_file = ref('')
  const raw_lines = ref([])
  const level_filter = ref('all')
  const keyword_filter = ref('')
  const page = ref(1)
  const page_size = ref(500)
  const loading = ref(false)

  const parsed_lines = computed(() => raw_lines.value.map(parse_line))

  const filtered_lines = computed(() => {
    let items = parsed_lines.value
    if (level_filter.value && level_filter.value !== 'all') {
      items = items.filter((item) => item.level === level_filter.value)
    }
    if (keyword_filter.value) {
      items = items.filter((item) => item.message.includes(keyword_filter.value))
    }
    return items
  })

  const total = computed(() => filtered_lines.value.length)

  const log_items = computed(() => {
    const start = (page.value - 1) * page_size.value
    return filtered_lines.value.slice(start, start + page_size.value)
  })

  async function fetch_file_list() {
    file_list.value = (await http.get('/api/logs')) || []
    return file_list.value
  }

  async function fetch_content() {
    if (!current_file.value) return
    loading.value = true
    try {
      raw_lines.value =
        (await http.get(`/api/logs/${encodeURIComponent(current_file.value)}`)) || []
    } finally {
      loading.value = false
    }
  }

  function select_file(name) {
    current_file.value = name
    page.value = 1
  }

  function set_level_filter(level) {
    level_filter.value = level
    page.value = 1
  }

  function set_keyword_filter(keyword) {
    keyword_filter.value = keyword
    page.value = 1
  }

  function set_page(value) {
    page.value = value
  }

  // ---------- 实时日志（跨页面共享缓存） ----------
  const live_logs = ref([])
  const live_max_seq = ref(0)
  // 每收到一条新日志自增，供页面 watch 触发自动滚动
  // （watch 数组 ref 的 push 不会触发，必须依赖该计数器）
  const live_version = ref(0)
  /** 最新日志（倒序，上限 MAX_RECENT_LOGS）：供首页直接渲染，无需每次 reverse + slice */
  const recent_logs = ref([])
  // 订阅句柄仅保存以防丢失：实时日志订阅是应用生命周期级的单例，
  // 缓存跨页面保留，登出时由 clear_live() 清空数据、连接由 use_websocket 统一管理
  let live_subscription = null
  let live_history_subscription = null
  let live_initialized = false

  function push_live(log) {
    // 用 seq 去重：断线重连后补发的历史日志可能与实时推送重复
    if (typeof log.seq === 'number') {
      if (log.seq <= live_max_seq.value) return
      live_max_seq.value = log.seq
    }
    live_logs.value.push(log)
    if (live_logs.value.length > MAX_LIVE_LOGS) {
      live_logs.value.splice(0, live_logs.value.length - MAX_LIVE_LOGS)
    }
    // 倒序缓存：unshift 后截断，单次开销 O(上限)，与总条数无关
    recent_logs.value.unshift(log)
    if (recent_logs.value.length > MAX_RECENT_LOGS) {
      recent_logs.value.length = MAX_RECENT_LOGS
    }
    live_version.value += 1
  }

  /** 启动实时日志订阅（幂等，任意页面调用一次即可，缓存跨页面保留） */
  function init_live() {
    if (live_initialized) return
    live_initialized = true
    const { on_event } = use_websocket()
    live_subscription = on_event('log', push_live)
    // log_history 是订阅 log 后服务端补发的历史缓存，仅监听、不重复订阅
    live_history_subscription = on_event(
      'log_history',
      (logs) => {
        for (const log of logs) push_live(log)
      },
      { subscribe: false },
    )
  }

  function clear_live() {
    live_logs.value = []
    recent_logs.value = []
    live_max_seq.value = 0
  }

  return {
    file_list,
    current_file,
    log_items,
    total,
    page,
    page_size,
    level_filter,
    keyword_filter,
    loading,
    live_logs,
    recent_logs,
    live_version,
    fetch_file_list,
    fetch_content,
    select_file,
    set_level_filter,
    set_keyword_filter,
    set_page,
    init_live,
    clear_live,
  }
})
