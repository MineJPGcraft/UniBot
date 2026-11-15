/**
 * 服务器 Store：服务器列表、详情、指令执行、广播
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const useServerStore = defineStore('server', () => {
  const server_list = ref([])
  const loading = ref(false)

  async function fetch_server_list() {
    loading.value = true
    try {
      server_list.value = (await http.get('/api/servers')) || []
    } finally {
      loading.value = false
    }
    return server_list.value
  }

  async function fetch_server_detail(name) {
    return await http.get(`/api/servers/${encodeURIComponent(name)}`)
  }

  /** 执行 RCON 指令，name 为 all 时广播到所有服务器 */
  async function execute_command(name, command) {
    return await http.post(`/api/servers/${encodeURIComponent(name)}/execute`, { command })
  }

  async function fetch_server_players(name) {
    return await http.get(`/api/servers/${encodeURIComponent(name)}/players`)
  }

  async function broadcast_message(message) {
    return await http.post('/api/servers/broadcast', { message })
  }

  return {
    server_list,
    loading,
    fetch_server_list,
    fetch_server_detail,
    fetch_server_players,
    execute_command,
    broadcast_message,
  }
})
