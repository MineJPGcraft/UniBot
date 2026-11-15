/**
 * 全局重启控制
 * 复用 Sidebar 的重启逻辑，并提供「操作后询问是否重启」的能力。
 * 模块级共享状态，任意组件通过 use_restart() 触发。
 */
import { ref } from 'vue'
import { t_global } from '@/i18n'
import { use_toast } from '@/composables/use_toast'
import { http } from '@/utils/http'

const prompt_open = ref(false)
const prompt_title = ref('')
const prompt_message = ref('')
const restarting = ref(false)

// 等待重启的取消标志：用户关闭弹窗 / 登出时置位，终止健康检查循环
let waiting_cancelled = false

function cancel_wait() {
  waiting_cancelled = true
}

async function wait_for_restart(previous_started_at) {
  const toast = use_toast()
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (waiting_cancelled) {
      restarting.value = false
      return
    }
    await new Promise((resolve) => window.setTimeout(resolve, 500))
    if (waiting_cancelled) {
      restarting.value = false
      return
    }
    try {
      const health = await http.get('/api/status/health', { auth: false })
      if (health.started_at !== previous_started_at) {
        restarting.value = false
        window.location.reload()
        return
      }
    } catch {
      // 服务重启期间健康检查暂时不可用。
    }
  }
  restarting.value = false
  toast.error(t_global('ui.restart_timeout'))
}

async function restart_bot() {
  const toast = use_toast()
  restarting.value = true
  waiting_cancelled = false
  try {
    const previous_instance = await http.post('/api/status/restart', {})
    prompt_open.value = false
    toast.success(t_global('ui.restart_started'))
    await wait_for_restart(previous_instance.started_at)
  } catch (error) {
    restarting.value = false
    toast.error(error.message || t_global('ui.restart_failed'))
  }
}

export function use_restart() {
  /** 弹出「是否立即重启」询问框，message 用于说明触发原因 */
  function ask_restart(
    message = t_global('ui.restart_default_message'),
    title = t_global('ui.restart_default_title'),
  ) {
    if (restarting.value) return
    prompt_title.value = title
    prompt_message.value = message
    prompt_open.value = true
  }

  function close_prompt() {
    prompt_open.value = false
    // 关闭询问框即放弃本次等待，避免后台继续轮询并在完成后强制刷新页面
    if (restarting.value) cancel_wait()
  }

  return {
    prompt_open,
    prompt_title,
    prompt_message,
    restarting,
    restart_bot,
    ask_restart,
    close_prompt,
  }
}
