<script setup>
/**
 * 保存前 diff 预览弹窗：展示变更列表并确认提交。
 * Config.toml 与 .env 两个保存流程共用，仅文案与数据不同。
 */
import { Icon } from '@iconify/vue'
import Dialog from '@/components/ui/Dialog.vue'
import { useI18n } from 'vue-i18n'

defineProps({
  /** 弹窗开关 */
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  /** 变更列表：[{ key, label, old_value, new_value }] */
  changes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'confirm'])

const { t } = useI18n()

function display_value(value) {
  if (value === undefined || value === null || value === '') {
    return t('config_view.diff_empty_value')
  }
  if (typeof value === 'boolean') {
    return value ? t('config_view.diff_value_on') : t('config_view.diff_value_off')
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : t('config_view.diff_empty_list')
  }
  return String(value)
}
</script>

<template>
  <Dialog
    :open="open"
    :title="title"
    :description="description"
    :confirm-text="t('config_view.diff_confirm_save')"
    :loading="loading"
    @update:open="(value) => emit('update:open', value)"
    @confirm="emit('confirm')"
  >
    <ul class="diff-list">
      <li v-for="change in changes" :key="change.key" class="diff-item">
        <div class="diff-label">{{ change.label }}</div>
        <div class="diff-values mono">
          <span class="diff-old">{{ display_value(change.old_value) }}</span>
          <Icon icon="lucide:arrow-right" width="13" class="text-muted" />
          <span class="diff-new">{{ display_value(change.new_value) }}</span>
        </div>
      </li>
    </ul>
  </Dialog>
</template>

<style scoped>
.diff-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 320px;
  overflow-y: auto;
}

.diff-item {
  padding: var(--space-3);
  background: var(--surface-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.diff-label {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.diff-values {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  flex-wrap: wrap;
}

.diff-old {
  color: var(--danger);
  text-decoration: line-through;
}

.diff-new {
  color: var(--success);
  font-weight: 600;
}
</style>
