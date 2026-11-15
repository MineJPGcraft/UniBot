<script setup>
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_toast } from '@/composables/use_toast'
import CodeEditor from './CodeEditor.vue'

const { t } = useI18n()

const props = defineProps({
  /** 面板标题，展示在头部左侧 */
  title: { type: String, default: '' },
  /** 高亮语言：toml | properties | yaml */
  language: { type: String, default: 'toml' },
  /** 代码内容（只读展示，带语法着色） */
  code: { type: String, required: true },
})

const toast = use_toast()

async function copy_code() {
  try {
    await navigator.clipboard.writeText(props.code)
    toast.success(t('common.copy_success'))
  } catch {
    toast.error(t('common.copy_failed'))
  }
}
</script>

<template>
  <div class="ui-code-panel">
    <div class="ui-code-panel-head">
      <span class="ui-code-panel-title">{{ title }}</span>
      <button class="ui-code-panel-copy" type="button" @click="copy_code">
        <Icon icon="lucide:copy" width="13" />
        {{ t('common.copy') }}
      </button>
    </div>
    <CodeEditor
      class="ui-code-panel-editor"
      :model-value="code"
      :language="language"
      read-only
      min-height="0"
    />
  </div>
</template>

<style scoped>
.ui-code-panel {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.ui-code-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-sunken);
  border-bottom: 1px solid var(--border);
}

.ui-code-panel-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
}

.ui-code-panel-copy {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px var(--space-2);
  border: none;
  border-radius: var(--radius);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-xs);
  cursor: pointer;
  transition:
    color var(--transition),
    background-color var(--transition);
}

.ui-code-panel-copy:hover {
  color: var(--accent);
  background: var(--accent-soft);
}

/* 覆盖编辑器自身边框，由面板统一提供 */
.ui-code-panel-editor {
  border: none;
  border-radius: 0;
}

.ui-code-panel-editor :deep(.cm-scroller) {
  padding-bottom: var(--space-3);
}
</style>
