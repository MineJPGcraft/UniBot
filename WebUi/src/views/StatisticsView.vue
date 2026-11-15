<script setup>
import {
  computed,
  defineAsyncComponent,
  onActivated,
  onDeactivated,
  onMounted,
  onUnmounted,
  ref,
} from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useStatisticsStore } from '@/stores/statistics'
import { useAuthStore } from '@/stores/auth'
import { use_async_action } from '@/composables/use_async_action'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Select from '@/components/ui/Select.vue'
import { format_datetime } from '@/utils/format'

/** 异步组件：TrendChart 静态链会拖入 ECharts（约 180 kB gzip），改为按需加载 */
const TrendChart = defineAsyncComponent(() => import('@/components/charts/TrendChart.vue'))

const AUTO_REFRESH_INTERVAL_MS = 60000

const statistics_store = useStatisticsStore()
const auth_store = useAuthStore()
const { t } = useI18n()
const { statistics } = storeToRefs(statistics_store)
const { run } = use_async_action()

const trend_days = ref('30')
const reset_dialog_open = ref(false)
const resetting = ref(false)

const trend_options = computed(() => [
  { value: '7', label: t('statistics.trend_last_7_days') },
  { value: '14', label: t('statistics.trend_last_14_days') },
  { value: '30', label: t('statistics.trend_last_30_days') },
])

const summary_items = computed(() => [
  {
    label: t('statistics.summary_sent_total'),
    value: statistics.value?.summary?.sent_total ?? '—',
    icon: 'lucide:message-square-share',
  },
  {
    label: t('statistics.summary_received_total'),
    value: statistics.value?.summary?.received_total ?? '—',
    icon: 'lucide:inbox',
  },
  {
    label: t('statistics.summary_group_messages'),
    value: statistics.value?.summary?.group_received_total ?? '—',
    icon: 'lucide:users-round',
  },
  {
    label: t('statistics.summary_active_groups'),
    value: statistics.value?.summary?.active_groups_today ?? '—',
    icon: 'lucide:flame',
  },
])

/** 趋势图数据与序列定义（颜色为字面量，对应 --accent / --success，ECharts canvas 不支持 CSS 变量） */
const trend_series = computed(() => [
  { key: 'received', name: t('statistics.series_received'), color: '#2563eb' },
  { key: 'sent', name: t('statistics.series_sent'), color: '#16a34a' },
])
const trend_items = computed(() =>
  (statistics.value?.trend || []).map((day) => ({
    label: day.date,
    received: day.received,
    sent: day.sent,
  })),
)

const chart_type_options = computed(() => [
  { value: 'bar', label: t('statistics.chart_type_bar') },
  { value: 'line', label: t('statistics.chart_type_line') },
])
const chart_type = ref('bar')

/** 活跃群聊排行 */
const active_groups = computed(() => statistics.value?.groups || [])

/** 平台分布（相对条形宽度） */
const platform_rank = computed(() => statistics.value?.platforms || [])
const max_platform_count = computed(() =>
  Math.max(1, ...platform_rank.value.map((item) => item.count)),
)

const connected_bots = computed(() => statistics.value?.bots || [])

async function refresh() {
  await run(
    () => statistics_store.fetch_statistics(Number(trend_days.value)),
    t('statistics.fetch_failed'),
  )
}

/** 群聊最近活跃时间（Unix 秒）转可读格式 */
function format_active_time(timestamp_seconds) {
  return format_datetime(new Date(timestamp_seconds * 1000).toISOString())
}

async function confirm_reset() {
  const ok = await run(
    () => statistics_store.reset_statistics(),
    t('statistics.reset_failed'),
    resetting,
  )
  if (ok) reset_dialog_open.value = false
}

let refresh_timer = null

function start_timer() {
  if (refresh_timer) return
  refresh_timer = setInterval(refresh, AUTO_REFRESH_INTERVAL_MS)
}

function stop_timer() {
  if (!refresh_timer) return
  clearInterval(refresh_timer)
  refresh_timer = null
}

/** 页面不可见时暂停 60s 轮询与图表重算，回到前台立即刷新一次 */
function handle_visibility_change() {
  if (document.visibilityState === 'visible') {
    refresh()
    start_timer()
  } else {
    stop_timer()
  }
}

onMounted(() => {
  refresh()
  start_timer()
  document.addEventListener('visibilitychange', handle_visibility_change)
})

// KeepAlive 缓存：切走时暂停轮询，切回时刷新一次并恢复（首次激活由 onMounted 负责）
let activated_once = false
onActivated(() => {
  if (!activated_once) {
    activated_once = true
    return
  }
  if (document.visibilityState !== 'visible') return
  refresh()
  start_timer()
})

onDeactivated(() => stop_timer())

onUnmounted(() => {
  stop_timer()
  document.removeEventListener('visibilitychange', handle_visibility_change)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('statistics.page_title') }}</h1>
        <p class="page-desc">{{ t('statistics.page_description') }}</p>
      </div>
      <div class="page-actions">
        <Select v-model="trend_days" :options="trend_options" @update:model-value="refresh" />
        <Button variant="secondary" :loading="statistics_store.loading" @click="refresh">
          <Icon icon="lucide:refresh-cw" width="15" />
          {{ t('common.refresh') }}
        </Button>
        <Button v-if="auth_store.is_admin" variant="danger" @click="reset_dialog_open = true">
          <Icon icon="lucide:eraser" width="15" />
          {{ t('statistics.reset_action') }}
        </Button>
      </div>
    </div>

    <!-- 总览指标 -->
    <section class="stats-strip card">
      <div v-for="item in summary_items" :key="item.label" class="stat-cell">
        <Icon :icon="item.icon" width="16" class="stat-icon" />
        <div class="stat-body">
          <span class="stat-value">{{ item.value }}</span>
          <span class="stat-label">{{ item.label }}</span>
        </div>
      </div>
      <div class="stat-cell">
        <Icon icon="lucide:bot" width="16" class="stat-icon" />
        <div class="stat-body">
          <span class="stat-value">{{ connected_bots.length }}</span>
          <span class="stat-label">{{ t('statistics.summary_connected_bots') }}</span>
        </div>
      </div>
    </section>

    <!-- 消息趋势 -->
    <section class="card trend-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('statistics.trend_card_title') }}</h3>
        <div class="trend-actions">
          <Select v-model="chart_type" :options="chart_type_options" />
          <Badge variant="neutral">{{
            t('statistics.days_count_badge', { days: trend_days })
          }}</Badge>
        </div>
      </div>
      <div class="card-body">
        <TrendChart :items="trend_items" :series="trend_series" :type="chart_type" />
      </div>
    </section>

    <div class="detail-grid">
      <!-- 活跃群聊排行 -->
      <section class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('statistics.groups_card_title') }}</h3>
          <Badge variant="accent">
            {{
              t('statistics.tracked_groups_badge', {
                count: statistics?.summary?.tracked_groups ?? 0,
              })
            }}
          </Badge>
        </div>
        <div class="card-body group-panel">
          <EmptyState
            v-if="active_groups.length === 0"
            icon="lucide:message-circle-off"
            :title="t('statistics.groups_empty_title')"
            :description="t('statistics.groups_empty_description')"
          />
          <ul v-else class="group-rows">
            <li v-for="group in active_groups" :key="group.key" class="group-row">
              <Icon icon="lucide:message-circle" width="15" class="group-icon" />
              <div class="group-info">
                <span class="group-name">{{ group.name || group.key }}</span>
                <span v-if="group.name" class="group-key mono">{{ group.key }}</span>
              </div>
              <div class="group-meta">
                <span class="group-count">{{ group.received }}</span>
                <span class="group-time text-xs text-muted">{{
                  format_active_time(group.last_active)
                }}</span>
              </div>
            </li>
          </ul>
        </div>
      </section>

      <div class="side-column">
        <!-- 平台分布 -->
        <section class="card">
          <div class="card-header">
            <h3 class="card-title">{{ t('statistics.platforms_card_title') }}</h3>
          </div>
          <div class="card-body">
            <EmptyState
              v-if="platform_rank.length === 0"
              icon="lucide:radio"
              :title="t('statistics.platforms_empty_title')"
            />
            <ul v-else class="platform-rows">
              <li v-for="item in platform_rank" :key="item.platform" class="platform-row">
                <span class="platform-name">{{ item.platform }}</span>
                <div class="platform-bar-track">
                  <div
                    class="platform-bar"
                    :style="{ width: `${(item.count / max_platform_count) * 100}%` }"
                  />
                </div>
                <span class="platform-count mono">{{ item.count }}</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- 已连接机器人 -->
        <section class="card">
          <div class="card-header">
            <h3 class="card-title">{{ t('statistics.bots_card_title') }}</h3>
            <Badge :variant="connected_bots.length > 0 ? 'success' : 'danger'">
              {{
                connected_bots.length > 0
                  ? t('statistics.bots_online_badge', { count: connected_bots.length })
                  : t('statistics.bots_none_badge')
              }}
            </Badge>
          </div>
          <div class="card-body">
            <EmptyState
              v-if="connected_bots.length === 0"
              icon="lucide:unplug"
              :title="t('statistics.bots_empty_title')"
              :description="t('statistics.bots_empty_description')"
            />
            <ul v-else class="bot-rows">
              <li v-for="account in connected_bots" :key="account.self_id" class="bot-row">
                <span class="status-dot status-dot--on" />
                <span class="bot-id mono">{{ account.self_id }}</span>
                <Badge variant="neutral">
                  <Icon icon="lucide:plug" width="12" />
                  {{ account.adapter }}
                </Badge>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </div>

    <!-- 清空确认弹窗 -->
    <Dialog
      v-model="reset_dialog_open"
      :title="t('statistics.reset_dialog_title')"
      :description="t('statistics.reset_dialog_description')"
      :confirm-text="t('statistics.reset_dialog_confirm')"
      confirm-variant="danger"
      :loading="resetting"
      @confirm="confirm_reset"
    />
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* 总览指标条 */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  margin-bottom: var(--space-5);
}

.stat-cell {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
}

.stat-cell + .stat-cell {
  border-left: 1px solid var(--border);
}

.stat-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-value {
  font-size: var(--text-md);
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.trend-card {
  margin-bottom: var(--space-5);
}

.trend-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 双栏明细 */
.detail-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: var(--space-5);
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* 活跃群聊 */
.group-panel {
  padding: 0;
}

.group-rows {
  display: flex;
  flex-direction: column;
}

.group-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border);
}

.group-row:last-child {
  border-bottom: none;
}

.group-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.group-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.group-name {
  font-size: var(--text-sm);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-key {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.group-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}

.group-count {
  font-size: var(--text-sm);
  font-weight: 700;
}

/* 平台分布 */
.platform-rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.platform-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.platform-name {
  width: 88px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.platform-bar-track {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--surface-sunken);
  overflow: hidden;
}

.platform-bar {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
  opacity: 0.75;
}

.platform-count {
  width: 48px;
  text-align: right;
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 已连接机器人 */
.bot-rows {
  display: flex;
  flex-direction: column;
}

.bot-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border);
}

.bot-row:last-child {
  border-bottom: none;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--on {
  background: var(--success);
}

.bot-id {
  flex: 1;
  font-size: var(--text-sm);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1100px) {
  .stats-strip {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-cell:nth-child(odd) {
    border-left: none;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
