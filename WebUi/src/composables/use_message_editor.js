import { ref, watch } from 'vue'

const STORAGE_KEY = 'unibot_message_editor_raw'

/**
 * 消息编辑器全局视图模式（所有消息共用、跨会话持久化）。
 *
 * - `false`（默认）：占位符视图，`{name}` 渲染为可拖拽的原子标签；
 * - `true`：原文视图，直接编辑 `{name}` 原始文本，方便直接选中替换。
 *
 * 以模块级单例 ref 承载，由 MessageTree 工具栏统一开关，各消息编辑器共享同一状态。
 */
const raw_mode = ref(localStorage.getItem(STORAGE_KEY) === '1')

watch(raw_mode, (value) => {
  localStorage.setItem(STORAGE_KEY, value ? '1' : '0')
})

export function use_message_editor() {
  return { raw_mode }
}
