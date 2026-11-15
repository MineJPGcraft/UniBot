/**
 * 玩家绑定 Store：分页列表、绑定、解绑
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const usePlayerStore = defineStore('player', () => {
  const binding_list = ref([])
  const total = ref(0)
  const page = ref(1)
  const page_size = ref(20)
  const keyword = ref('')
  const loading = ref(false)

  async function fetch_bindings() {
    loading.value = true
    try {
      const data = await http.get('/api/players', {
        query: { page: page.value, page_size: page_size.value, keyword: keyword.value },
      })
      binding_list.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function bind_player(user, player) {
    await http.post('/api/players', { user, player })
    await fetch_bindings()
  }

  async function unbind_player(user, player) {
    await http.delete(`/api/players/${encodeURIComponent(user)}/${encodeURIComponent(player)}`)
    await fetch_bindings()
  }

  function set_keyword(value) {
    keyword.value = value
    page.value = 1
  }

  function set_page(value) {
    page.value = value
  }

  return {
    binding_list,
    total,
    page,
    page_size,
    keyword,
    loading,
    fetch_bindings,
    bind_player,
    unbind_player,
    set_keyword,
    set_page,
  }
})
