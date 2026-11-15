<script setup>
/**
 * 配置中心：带操作的页签顶部栏。
 *
 * 左侧为说明文字 / 次要按钮（`#left` 插槽，自动靠左），右侧为撤销与保存按钮。
 * 撤销按钮的禁用状态与改动数量由调用方传入。
 */
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/Button.vue'

const { t } = useI18n()

defineProps({
  /** 未保存改动数量；为 0 时禁用撤销与保存 */
  changeCount: { type: Number, default: 0 },
  /** 保存按钮 loading */
  saving: { type: Boolean, default: false },
  /** 保存按钮图标，空字符串则不显示图标 */
  saveIcon: { type: String, default: 'lucide:save' },
})

defineEmits(['revert', 'save'])
</script>

<template>
  <div class="tab-actions">
    <div class="tab-action-left">
      <slot name="left" />
    </div>
    <Button variant="ghost" :disabled="changeCount === 0" @click="emit('revert')">
      {{ t('config_view.revert_changes') }}
    </Button>
    <Button variant="primary" :disabled="changeCount === 0" :loading="saving" @click="emit('save')">
      <Icon v-if="saveIcon" :icon="saveIcon" width="15" />
      {{ t('config_view.save_changes') }}
      <span v-if="changeCount > 0" class="change-count">{{ changeCount }}</span>
    </Button>
  </div>
</template>

<style scoped>
.tab-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.tab-action-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-right: auto;
}

.change-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.25);
  font-size: var(--text-xs);
}
</style>
