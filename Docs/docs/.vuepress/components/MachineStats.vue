<template>
  <div ref="rootElement" class="machine-stats">
    <div v-for="stat in stats" :key="stat.label" class="stat-card">
      <div class="stat-label">{{ stat.label }}</div>
      <div class="stat-value">{{ stat.value }}</div>
    </div>
    <p v-if="error" class="stat-error">{{ errorLabel }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  onlineMachineLabel: { type: String, default: '在线机器' },
  totalMachineLabel: { type: String, default: '机器总数' },
  connectedBotLabel: { type: String, default: '已连接机器人' },
  sentTotalLabel: { type: String, default: '累计发送消息' },
  receivedTotalLabel: { type: String, default: '累计接收消息' },
  errorLabel: { type: String, default: '统计数据加载失败' },
})

// 机器注册服务器公开聚合状态接口
const STATS_API = 'https://bot-api.mcjpg.dev/status.php'

// 数字滚动动画：基准时长 + 每多一位数字加长，保证大数字收尾同样从容
const BASE_ANIMATION_DURATION = 1800
const DURATION_PER_EXTRA_DIGIT = 600
const ANIMATION_STAGGER = 160

// 按数值位数计算时长：3 位数约 1.8s，5 位数约 3s，6 位数约 3.6s
const durationFor = (target) => {
  const digits = String(Math.trunc(target)).length
  return BASE_ANIMATION_DURATION + Math.max(digits - 3, 0) * DURATION_PER_EXTRA_DIGIT
}

const onlineMachines = ref(0)
const totalMachines = ref(0)
const connectedBots = ref(0)
const sentTotal = ref(0)
const receivedTotal = ref(0)
const error = ref(false)
const rootElement = ref(null)

const animationFrames = []
let intersectionObserver = null
// 数据已就绪但尚未进入视口时，暂存待播放的目标值
let pendingTargets = null
let hasAnimated = false

const formatNumber = (value) => value.toLocaleString('en-US')

// 缓出曲线：开局冲刺极快，随后大幅放缓，最后缓慢逼近并稳定在目标值
const easeOutExpo = (progress) => (progress >= 1 ? 1 : 1 - Math.pow(2, -10 * progress))

// 从 0 滚动递增到目标值，最终精确停在 target 上
const animateValue = (target, apply, delay = 0) => {
  if (target <= 0) {
    apply(0)
    return
  }
  const duration = durationFor(target)
  const startAt = performance.now() + delay
  const step = (now) => {
    const progress = Math.min(Math.max((now - startAt) / duration, 0), 1)
    apply(Math.round(target * easeOutExpo(progress)))
    if (progress < 1) {
      animationFrames.push(requestAnimationFrame(step))
    }
  }
  animationFrames.push(requestAnimationFrame(step))
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// 播放数字滚动动画（或直接显示最终值）
const playAnimation = (targets) => {
  if (prefersReducedMotion()) {
    targets.forEach(([target, apply]) => apply(target))
    return
  }
  targets.forEach(([target, apply], index) => animateValue(target, apply, index * ANIMATION_STAGGER))
}

// 组件滚动进入视口后触发一次动画
const startAnimationWhenVisible = () => {
  if (hasAnimated) {
    return
  }
  hasAnimated = true
  if (pendingTargets) {
    playAnimation(pendingTargets)
    pendingTargets = null
  }
  intersectionObserver?.disconnect()
  intersectionObserver = null
}

const stats = computed(() => [
  { label: props.onlineMachineLabel, value: formatNumber(onlineMachines.value) },
  { label: props.totalMachineLabel, value: formatNumber(totalMachines.value) },
  { label: props.connectedBotLabel, value: formatNumber(connectedBots.value) },
  { label: props.sentTotalLabel, value: formatNumber(sentTotal.value) },
  { label: props.receivedTotalLabel, value: formatNumber(receivedTotal.value) },
])

onMounted(async () => {
  // 先监听组件是否滚动进入视口，进入后才播放动画
  if (typeof IntersectionObserver === 'function' && rootElement.value) {
    intersectionObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          startAnimationWhenVisible()
        }
      },
      { threshold: 0.3 },
    )
    intersectionObserver.observe(rootElement.value)
  }

  try {
    const response = await fetch(STATS_API)
    const result = await response.json()
    const data = result?.data
    if (result.code === 0 && data && typeof data === 'object') {
      const targets = [
        [Number(data.online_machines) || 0, (value) => (onlineMachines.value = value)],
        [Number(data.all_machines) || 0, (value) => (totalMachines.value = value)],
        [Number(data.connected_bots) || 0, (value) => (connectedBots.value = value)],
        [Number(data.sent_total) || 0, (value) => (sentTotal.value = value)],
        [Number(data.received_total) || 0, (value) => (receivedTotal.value = value)],
      ]
      if (hasAnimated) {
        // 组件已在视口内（或浏览器不支持 IntersectionObserver），立即播放
        playAnimation(targets)
      } else {
        // 尚未进入视口，暂存目标值，等可见时再播放
        pendingTargets = targets
      }
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  }
})

onBeforeUnmount(() => {
  animationFrames.forEach((frame) => cancelAnimationFrame(frame))
  intersectionObserver?.disconnect()
  intersectionObserver = null
})
</script>

<style scoped>
.machine-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}

.stat-card {
  padding: 1rem 1.25rem;
  border-radius: 12px;
  border: 1px solid var(--vp-c-divider, #e2e2e3);
  text-align: center;
}

.stat-card:nth-child(odd) {
  background: linear-gradient(135deg, rgba(56, 132, 255, 0.08), rgba(56, 132, 255, 0.02));
}

.stat-card:nth-child(even) {
  background: linear-gradient(135deg, rgba(0, 180, 120, 0.08), rgba(0, 180, 120, 0.02));
}

.stat-label {
  font-size: 0.875rem;
  color: var(--vp-c-text-2, #6b7280);
}

.stat-value {
  margin-top: 0.25rem;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--vp-c-text-1, #1a1a1a);
}

.stat-error {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 0.875rem;
  color: #e5484d;
}
</style>
