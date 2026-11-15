/**
 * 全局轻提示（Toast）
 * 模块级共享队列，任意组件通过 use_toast() 触发
 */
import { ref } from 'vue'

const toast_list = ref([])
const toast_timers = new Map()
let toast_id = 0

function push_toast(type, message, duration = 3000) {
  const id = ++toast_id
  toast_list.value.push({ id, type, message })
  if (duration > 0) {
    toast_timers.set(
      id,
      setTimeout(() => dismiss_toast(id), duration),
    )
  }
}

function dismiss_toast(id) {
  const timer_id = toast_timers.get(id)
  if (timer_id !== undefined) {
    clearTimeout(timer_id)
    toast_timers.delete(id)
  }
  toast_list.value = toast_list.value.filter((toast) => toast.id !== id)
}

export function use_toast() {
  return {
    toast_list,
    dismiss_toast,
    success: (message) => push_toast('success', message),
    error: (message) => push_toast('error', message, 4500),
    info: (message) => push_toast('info', message),
  }
}
