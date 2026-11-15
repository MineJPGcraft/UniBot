/**
 * 适配器 Store：适配器目录、注册状态与安装管理
 *
 * 安装/卸载会触发依赖变更（uv add / uv remove），后端以任务中心任务执行，
 * 接口立即返回任务快照。等待任务结束与重启询问统一交给
 * `composables/use_task_submit.js`，本 store 只负责请求与列表刷新。
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/utils/http'

export const useAdapterStore = defineStore('adapter', () => {
  const registered_list = ref([])
  const catalog = ref([])
  const loading = ref(false)

  /** 获取适配器注册列表与目录；`silent` 用于语言切换等后台刷新（不触发 loading） */
  async function fetch_all({ silent = false } = {}) {
    if (!silent) loading.value = true
    try {
      const data = await http.get('/api/config/nonebot')
      registered_list.value = data.adapters || []
      catalog.value = data.adapter_catalog || []
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** 提交安装任务，返回任务快照 */
  async function install(adapter_id) {
    const task = await http.post('/api/config/nonebot/adapters/install', { adapter_id })
    await fetch_all()
    return task
  }

  async function toggle_register(name, module_name, register) {
    if (register) {
      await http.post('/api/config/nonebot/adapters', { name, module_name })
    } else {
      await http.delete('/api/config/nonebot/adapters', { body: { name, module_name } })
    }
    await fetch_all()
  }

  /** 提交卸载任务，返回任务快照 */
  async function uninstall(name, module_name) {
    const task = await http.delete('/api/config/nonebot/adapters/uninstall', {
      body: { name, module_name },
    })
    await fetch_all()
    return task
  }

  return {
    registered_list,
    catalog,
    loading,
    fetch_all,
    install,
    toggle_register,
    uninstall,
  }
})
