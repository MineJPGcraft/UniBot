<script setup>
import { computed, useId } from 'vue'
import {
  DrawerRoot,
  DrawerTrigger,
  DrawerPortal,
  DrawerOverlay,
  DrawerPopup,
  DrawerTitle,
  DrawerDescription,
  DrawerClose,
} from 'reka-ui'
import { Icon } from '@iconify/vue'

const open = defineModel({ type: Boolean, default: false })

const description_id = useId()

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  // 抽屉附着边：right（默认，右上角任务中心入口）/ left / top / bottom
  direction: { type: String, default: 'right' },
  width: { type: String, default: 'min(460px, 100vw)' },
  hideClose: { type: Boolean, default: false },
})

const panel_style = computed(() => {
  if (props.direction === 'left' || props.direction === 'right') {
    return { width: props.width }
  }
  return { maxHeight: props.width }
})
</script>

<template>
  <DrawerRoot :open="open" :swipe-direction="direction" @update:open="(value) => (open = value)">
    <DrawerTrigger v-if="$slots.trigger" as-child>
      <slot name="trigger" />
    </DrawerTrigger>
    <DrawerPortal>
      <DrawerOverlay class="ui-drawer-overlay" />
      <DrawerPopup
        class="ui-drawer-popup"
        :class="`ui-drawer-popup--${direction}`"
        :style="panel_style"
        :aria-describedby="description ? description_id : undefined"
      >
        <header class="ui-drawer-header">
          <div class="ui-drawer-heading">
            <DrawerTitle class="ui-drawer-title">{{ title }}</DrawerTitle>
            <DrawerDescription
              v-if="description"
              :id="description_id"
              class="ui-drawer-description"
            >
              {{ description }}
            </DrawerDescription>
          </div>
          <DrawerClose v-if="!hideClose" class="ui-drawer-close" aria-label="close">
            <Icon icon="lucide:x" width="16" />
          </DrawerClose>
        </header>
        <div class="ui-drawer-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="ui-drawer-footer">
          <slot name="footer" />
        </footer>
      </DrawerPopup>
    </DrawerPortal>
  </DrawerRoot>
</template>

<style>
/* Overlay / Popup 由 reka 经 Portal 渲染，scoped 的 data-v 属性无法命中
   （与 Dialog 同理），需非 scoped 声明，类名以 ui- 前缀保证唯一 */
@keyframes ui-drawer-overlay-fade-in {
  from {
    opacity: 0;
  }
}

@keyframes ui-drawer-slide-in-right {
  from {
    translate: 100% 0;
  }
}

@keyframes ui-drawer-slide-out-right {
  to {
    translate: 100% 0;
  }
}

@keyframes ui-drawer-slide-in-left {
  from {
    translate: -100% 0;
  }
}

@keyframes ui-drawer-slide-out-left {
  to {
    translate: -100% 0;
  }
}

@keyframes ui-drawer-slide-in-bottom {
  from {
    translate: 0 100%;
  }
}

@keyframes ui-drawer-slide-out-bottom {
  to {
    translate: 0 100%;
  }
}

@keyframes ui-drawer-slide-in-top {
  from {
    translate: 0 -100%;
  }
}

@keyframes ui-drawer-slide-out-top {
  to {
    translate: 0 -100%;
  }
}

.ui-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgb(24 24 27 / 0.35);
  z-index: var(--z-overlay);
  animation: ui-drawer-overlay-fade-in 150ms ease-out;
}

.ui-drawer-popup {
  position: fixed;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dialog);
  transition: transform 200ms ease-out;
}

.ui-drawer-popup:focus {
  outline: none;
}

.ui-drawer-popup[data-swiping] {
  transition-duration: 0ms;
}

.ui-drawer-popup--right {
  inset-block: 0;
  right: 0;
  max-width: 100vw;
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  transform: translateX(var(--drawer-swipe-movement-x, 0px));
}

.ui-drawer-popup--right[data-state='open'] {
  animation: ui-drawer-slide-in-right 220ms ease-out;
}

.ui-drawer-popup--right[data-state='closed'] {
  animation: ui-drawer-slide-out-right 200ms ease-out;
}

.ui-drawer-popup--left {
  inset-block: 0;
  left: 0;
  max-width: 100vw;
  border-left: none;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  transform: translateX(var(--drawer-swipe-movement-x, 0px));
}

.ui-drawer-popup--left[data-state='open'] {
  animation: ui-drawer-slide-in-left 220ms ease-out;
}

.ui-drawer-popup--left[data-state='closed'] {
  animation: ui-drawer-slide-out-left 200ms ease-out;
}

.ui-drawer-popup--bottom {
  inset-inline: 0;
  bottom: 0;
  border-bottom: none;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  transform: translateY(var(--drawer-swipe-movement-y, 0px));
}

.ui-drawer-popup--bottom[data-state='open'] {
  animation: ui-drawer-slide-in-bottom 220ms ease-out;
}

.ui-drawer-popup--bottom[data-state='closed'] {
  animation: ui-drawer-slide-out-bottom 200ms ease-out;
}

.ui-drawer-popup--top {
  inset-inline: 0;
  top: 0;
  border-top: none;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  transform: translateY(var(--drawer-swipe-movement-y, 0px));
}

.ui-drawer-popup--top[data-state='open'] {
  animation: ui-drawer-slide-in-top 220ms ease-out;
}

.ui-drawer-popup--top[data-state='closed'] {
  animation: ui-drawer-slide-out-top 200ms ease-out;
}
</style>

<style scoped>
.ui-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.ui-drawer-heading {
  min-width: 0;
}

.ui-drawer-title {
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.ui-drawer-description {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ui-drawer-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: var(--radius);
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.ui-drawer-close:hover {
  background: var(--hover);
  color: var(--text);
}

.ui-drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4) var(--space-5);
}

.ui-drawer-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
</style>
