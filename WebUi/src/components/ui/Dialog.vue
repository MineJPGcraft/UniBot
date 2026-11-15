<script setup>
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  DialogRoot,
  DialogTrigger,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from 'reka-ui'
import Button from './Button.vue'

const { t } = useI18n()

const open = defineModel({ type: Boolean, default: false })

const description_id = useId()

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  confirmText: { type: String, default: '' },
  cancelText: { type: String, default: '' },
  confirmVariant: { type: String, default: 'primary' },
  loading: { type: Boolean, default: false },
  hideFooter: { type: Boolean, default: false },
  width: { type: String, default: 'min(480px, calc(100vw - 32px))' },
})

defineEmits(['confirm'])

const confirm_text = computed(() => props.confirmText || t('common.confirm'))
const cancel_text = computed(() => props.cancelText || t('common.cancel'))
</script>

<template>
  <DialogRoot :open="open" @update:open="(value) => (open = value)">
    <DialogTrigger v-if="$slots.trigger" as-child>
      <slot name="trigger" />
    </DialogTrigger>
    <DialogPortal>
      <DialogOverlay class="ui-dialog-overlay" />
      <DialogContent
        class="ui-dialog-content"
        :style="{ width }"
        :aria-describedby="description ? description_id : undefined"
      >
        <DialogTitle class="ui-dialog-title">{{ title }}</DialogTitle>
        <DialogDescription v-if="description" :id="description_id" class="ui-dialog-description">
          {{ description }}
        </DialogDescription>
        <div class="ui-dialog-body">
          <slot />
        </div>
        <div v-if="!hideFooter" class="ui-dialog-footer">
          <DialogClose as-child>
            <Button variant="ghost">{{ cancel_text }}</Button>
          </DialogClose>
          <Button :variant="confirmVariant" :loading="loading" @click="$emit('confirm')">
            {{ confirm_text }}
          </Button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style>
/* Overlay / Content 由 reka 经 Portal 渲染，scoped 的 data-v 属性无法命中
   （Vue scopeId 继承在 popper/dismissable 包装层断裂），需非 scoped 声明；
   类名以 ui- 前缀保证唯一（先例：DropdownMenu / Select） */
@keyframes ui-dialog-overlay-fade-in {
  from {
    opacity: 0;
  }
}

@keyframes ui-dialog-pop-in {
  from {
    opacity: 0;
    transform: translate(-50%, -48%) scale(0.97);
  }
}

.ui-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgb(24 24 27 / 0.45);
  z-index: var(--z-overlay);
  animation: ui-dialog-overlay-fade-in 150ms ease-out;
}

.ui-dialog-content {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-height: 85vh;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-6);
  z-index: var(--z-dialog);
  animation: ui-dialog-pop-in 180ms ease-out;
}

.ui-dialog-content:focus {
  outline: none;
}

.ui-dialog-content::-webkit-scrollbar {
  display: none;
}
</style>

<style scoped>
.ui-dialog-title {
  font-size: var(--text-lg);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.ui-dialog-description {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.ui-dialog-body {
  margin-top: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.ui-dialog-footer {
  margin-top: var(--space-6);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
