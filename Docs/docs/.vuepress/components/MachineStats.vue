<template>
  <div class="machine-stats">
    <div class="stat-card">
      <div class="stat-label">{{ onlineLabel }}</div>
      <div class="stat-value">{{ onlineCount }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">{{ totalLabel }}</div>
      <div class="stat-value">{{ totalCount }}</div>
    </div>
    <p v-if="error" class="stat-error">{{ errorLabel }}</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

defineProps({
  onlineLabel: { type: String, default: '在线机器人' },
  totalLabel: { type: String, default: '累计使用机器' },
  errorLabel: { type: String, default: '统计数据加载失败' },
})

// 机器注册服务器状态接口
const STATS_API = 'https://bot-api.mcjpg.dev/status.php'

const onlineCount = ref(0)
const totalCount = ref(0)
const error = ref(false)

onMounted(async () => {
  try {
    const response = await fetch(STATS_API)
    const result = await response.json()
    if (result.code === 0 && Array.isArray(result.data)) {
      totalCount.value = result.data.length
      onlineCount.value = result.data.filter((machine) => machine.online).length
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  }
})
</script>

<style scoped>
.machine-stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 1.5rem 0;
}

.stat-card {
  flex: 1;
  min-width: 160px;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  border: 1px solid var(--vp-c-divider, #e2e2e3);
  background: linear-gradient(135deg, rgba(56, 132, 255, 0.08), rgba(56, 132, 255, 0.02));
  text-align: center;
}

.stat-card + .stat-card {
  background: linear-gradient(135deg, rgba(0, 180, 120, 0.08), rgba(0, 180, 120, 0.02));
}

.stat-label {
  font-size: 0.875rem;
  color: var(--vp-c-text-2, #6b7280);
}

.stat-value {
  margin-top: 0.25rem;
  font-size: 2rem;
  font-weight: 700;
  color: var(--vp-c-text-1, #1a1a1a);
}

.stat-error {
  width: 100%;
  margin: 0;
  font-size: 0.875rem;
  color: #e5484d;
}
</style>
