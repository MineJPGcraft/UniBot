<template>
  <div class="machine-stats">
    <div v-for="stat in stats" :key="stat.label" class="stat-card">
      <div class="stat-label">{{ stat.label }}</div>
      <div class="stat-value">{{ stat.value }}</div>
    </div>
    <p v-if="error" class="stat-error">{{ errorLabel }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

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

const onlineMachines = ref(0)
const totalMachines = ref(0)
const connectedBots = ref(0)
const sentTotal = ref(0)
const receivedTotal = ref(0)
const error = ref(false)

const formatNumber = (value) => value.toLocaleString('en-US')

const stats = computed(() => [
  { label: props.onlineMachineLabel, value: formatNumber(onlineMachines.value) },
  { label: props.totalMachineLabel, value: formatNumber(totalMachines.value) },
  { label: props.connectedBotLabel, value: formatNumber(connectedBots.value) },
  { label: props.sentTotalLabel, value: formatNumber(sentTotal.value) },
  { label: props.receivedTotalLabel, value: formatNumber(receivedTotal.value) },
])

onMounted(async () => {
  try {
    const response = await fetch(STATS_API)
    const result = await response.json()
    const data = result?.data
    if (result.code === 0 && data && typeof data === 'object') {
      onlineMachines.value = Number(data.online_machines) || 0
      totalMachines.value = Number(data.all_machines) || 0
      connectedBots.value = Number(data.connected_bots) || 0
      sentTotal.value = Number(data.sent_total) || 0
      receivedTotal.value = Number(data.received_total) || 0
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
