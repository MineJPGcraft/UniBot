/**
 * 数据统计 Store：消息统计、活跃群聊与已连接机器人
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const useStatisticsStore = defineStore('statistics', () => {
  const statistics = ref(null)
  const loading = ref(false)

  /** 获取统计数据（days 为趋势天数） */
  async function fetch_statistics(days = 30) {
    loading.value = true
    try {
      statistics.value = await http.get('/api/statistics', { query: { days } })
    } finally {
      loading.value = false
    }
    return statistics.value
  }

  /** 清空全部统计数据（后端会立即落盘） */
  async function reset_statistics() {
    await http.post('/api/statistics/reset')
    return fetch_statistics()
  }

  return { statistics, loading, fetch_statistics, reset_statistics }
})
