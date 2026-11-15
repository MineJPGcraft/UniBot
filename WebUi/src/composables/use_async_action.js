/**
 * 异步动作包装：统一「busy 标志 + 失败 toast」样板。
 *
 * 用法：
 *   const { run, busy } = use_async_action()
 *   const ok = await run(() => store.fetch_xxx(), '获取数据失败')
 *   if (ok) { /* 成功后的收尾 *\/ }
 *   // 多个独立 busy 标志时传入自定义 ref：
 *   await run(() => store.save(), '保存失败', saving)
 */
import { ref } from 'vue'
import { t_global } from '@/i18n'
import { use_toast } from '@/composables/use_toast'

export function use_async_action() {
  const busy = ref(false)
  const toast = use_toast()

  /**
   * 执行异步动作，自动维护 busy 标志并在失败时 toast 提示。
   * @param {() => Promise<any>} action 异步动作
   * @param {string} failure_message 失败兜底提示（优先展示 error.message）
   * @param {{ value: boolean }} [busy_ref] 外部 busy 标志（缺省用内部 busy）
   * @returns {Promise<boolean>} 动作是否成功
   */
  async function run(
    action,
    failure_message = t_global('common.operation_failed'),
    busy_ref = busy,
  ) {
    busy_ref.value = true
    try {
      await action()
      return true
    } catch (error) {
      toast.error(error?.message || failure_message)
      return false
    } finally {
      busy_ref.value = false
    }
  }

  return { run, busy }
}
