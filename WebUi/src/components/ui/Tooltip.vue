<script setup>
import { TooltipRoot, TooltipTrigger, TooltipPortal, TooltipContent } from 'reka-ui'

defineProps({
  text: { type: String, required: true },
})
</script>

<template>
  <TooltipRoot>
    <TooltipTrigger as-child>
      <slot />
    </TooltipTrigger>
    <TooltipPortal>
      <TooltipContent class="ui-tooltip-content" :side-offset="6">
        {{ text }}
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
</template>

<style scoped>
/* TooltipPortal 会把内容传送到 body，脱离组件 DOM 子树，
   scoped 的 data-v 属性无法命中（Vue 的 scopeId 不跨越 reka 的
   popper wrapper 层级），故用 :global 声明；类名以 ui- 前缀保证唯一 */
:global(.ui-tooltip-content) {
  position: relative;
  padding: var(--space-1) var(--space-2);
  background: var(--tooltip-bg);
  border: 1px solid var(--tooltip-border);
  color: var(--tooltip-fg);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  box-shadow: var(--shadow-md);
  z-index: var(--z-tooltip);
  animation: ui-tooltip-fade-in 120ms ease-out;
}
</style>
