<script setup>
/**
 * 玩家头像：加载失败自动隐藏图片并显示首字母兜底。
 * 头像走后端缓存接口，避免重复请求外部 CDN。
 */
import { computed } from 'vue'
import { api_url } from '@/utils/http'

const props = defineProps({
  /** 玩家名 */
  name: { type: String, required: true },
  /** 头像边长（px） */
  size: { type: Number, default: 24 },
})

const avatar_url = computed(
  () => `${api_url(`/api/players/${encodeURIComponent(props.name)}/avatar`)}`,
)

const fallback_initial = computed(() => props.name.slice(0, 1).toUpperCase())

function hide_broken_image(event) {
  event.target.style.display = 'none'
}
</script>

<template>
  <span class="player-head-wrap" :style="{ width: `${size}px`, height: `${size}px` }">
    <img
      class="player-head"
      :src="avatar_url"
      :width="size"
      :height="size"
      alt=""
      loading="lazy"
      @error="hide_broken_image"
    />
    <span class="player-head-fallback" :style="{ fontSize: `${Math.round(size / 2)}px` }">
      {{ fallback_initial }}
    </span>
  </span>
</template>

<style scoped>
.player-head-wrap {
  position: relative;
  flex-shrink: 0;
}

.player-head {
  position: relative;
  z-index: 1;
  border-radius: 4px;
  image-rendering: pixelated;
  background: var(--surface-sunken);
}

.player-head-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--surface-sunken);
  border-radius: 4px;
}
</style>
