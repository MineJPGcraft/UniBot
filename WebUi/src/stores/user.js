/**
 * 用户管理 Store（仅 admin 使用）
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const useUserStore = defineStore('user', () => {
  const user_list = ref([])
  const total = ref(0)
  const page = ref(1)
  const page_size = ref(20)
  const keyword = ref('')
  const loading = ref(false)

  async function fetch_users() {
    loading.value = true
    try {
      const data = await http.get('/api/users', {
        query: { page: page.value, page_size: page_size.value, keyword: keyword.value },
      })
      user_list.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function create_user(payload) {
    await http.post('/api/users', payload)
    await fetch_users()
  }

  async function update_user(user_id, payload) {
    await http.put(`/api/users/${encodeURIComponent(user_id)}`, payload)
    await fetch_users()
  }

  async function reset_password(user_id, password) {
    await http.put(`/api/users/${encodeURIComponent(user_id)}/password`, { password })
  }

  async function delete_user(user_id) {
    await http.delete(`/api/users/${encodeURIComponent(user_id)}`)
    await fetch_users()
  }

  function set_keyword(value) {
    keyword.value = value
    page.value = 1
  }

  function set_page(value) {
    page.value = value
  }

  return {
    user_list,
    total,
    page,
    page_size,
    keyword,
    loading,
    fetch_users,
    create_user,
    update_user,
    reset_password,
    delete_user,
    set_keyword,
    set_page,
  }
})
