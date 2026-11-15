/**
 * 任务提交流程：提交 → 等任务结束 → 按需询问重启。
 *
 * 需要依赖安装 / 卸载的操作（适配器安装卸载、插件安装升级卸载、扩展安装卸载）
 * 后端都以任务中心任务执行：接口立即返回任务快照，真正的依赖变更在任务体里
 * 完成。这里等待任务结束，失败即抛错，成功且 `result.restart_required` 为真时
 * 由调用方决定是否弹「立即重启」询问。
 *
 * 用法：
 *   const { submit_task } = use_task_submit()
 *   const { t } = useI18n()
 *   const task = await submit_task(() => store.install_adapter(id), '安装失败')
 *   maybe_ask_restart(task, t('adapters.restart_after_install_confirm', { name }))
 */
import { useI18n } from 'vue-i18n'
import { t_global } from '@/i18n'
import { useTaskStore } from '@/stores/task'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'

export function use_task_submit() {
  const { t } = useI18n()
  const toast = use_toast()
  const task_store = useTaskStore()
  const { ask_restart } = use_restart()

  /**
   * 提交后台任务并等待其结束。
   *
   * 任务失败时 toast 并返回 null；超时未结束时任务仍在后台继续，
   * 此时返回当前快照（调用方按 status 自行判断）。
   *
   * @param {() => Promise<object>} submit 返回任务快照的提交动作
   * @param {string} failure_message 失败兜底提示
   * @returns {Promise<object|null>} 最终任务快照，失败返回 null
   */
  async function submit_task(submit, failure_message = t_global('common.operation_failed')) {
    let task = null
    try {
      task = await submit()
    } catch (error) {
      toast.error(error?.message || failure_message)
      return null
    }
    if (!task?.id) return task
    const finished = (await task_store.wait_task(task.id)) || task
    if (finished.status === 'failed') {
      toast.error(finished.error || failure_message)
      return null
    }
    return finished
  }

  /**
   * 任务要求重启时弹出询问框（后端在任务体里标记 result.restart_required）。
   *
   * @param {object|null} task 已结束的任务快照
   * @param {string} message 询问文案（说明哪个操作触发了重启）
   */
  function maybe_ask_restart(task, message) {
    if (!task?.result?.restart_required) return
    ask_restart(message || t('ui.restart_default_message'))
  }

  return { submit_task, maybe_ask_restart }
}
