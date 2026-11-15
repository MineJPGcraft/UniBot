<script setup>
import { ref, computed, onActivated, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useStatusStore } from '@/stores/status'
import { useServerStore } from '@/stores/server'
import { useLogStore } from '@/stores/log'
import { use_websocket } from '@/composables/use_websocket'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SetupGuide from '@/components/SetupGuide.vue'
import { format_uptime, level_class, format_mb } from '@/utils/format'
import { cached_ansi_html } from '@/utils/ansi'
import { useThemeStore } from '@/stores/theme'
import { server_type_icon, server_type_label } from '@/utils/server'

const router = useRouter()
const { t } = useI18n()
const { is_dark } = storeToRefs(useThemeStore())
const status_store = useStatusStore()
const server_store = useServerStore()
const log_store = useLogStore()
const { status } = storeToRefs(status_store)
const { server_list } = storeToRefs(server_store)
const { recent_logs } = storeToRefs(log_store)
const { connection_state } = use_websocket()

/** 首页展示最近 80 条实时日志（倒序缓存由 store 维护，此处直接取用） */
const display_logs = computed(() => recent_logs.value)

const memory_percent = computed(() => {
  const memory_mb = status.value?.memory_mb || 0
  return Math.min(100, (memory_mb / 1024) * 100)
})

const online_count = computed(() => server_list.value.filter((server) => server.online).length)

const stat_items = computed(() => [
  {
    label: t('dashboard.dashboard_stat_version'),
    value: status.value?.version || '—',
    icon: 'lucide:tag',
  },
  {
    label: t('dashboard.dashboard_stat_uptime'),
    value: format_uptime(status.value?.uptime),
    icon: 'lucide:timer',
  },
  {
    label: t('dashboard.dashboard_stat_players_bound'),
    value: status.value?.players_bound ?? '—',
    icon: 'lucide:users',
  },
  {
    label: t('dashboard.dashboard_stat_ws_clients'),
    value: status.value?.ws_clients ?? '—',
    icon: 'lucide:radio',
  },
])

onMounted(async () => {
  server_store.fetch_server_list().catch((error) => console.warn('fetch_server_list failed', error))
  // 实时日志由共享 store 缓存，离开页面再回来日志仍保留
  log_store.init_live()
})

// 页面被 KeepAlive 缓存：切回时静默刷新服务器列表（首次挂载由 onMounted 负责，不重复请求）
let activated_once = false
onActivated(() => {
  if (!activated_once) {
    activated_once = true
    return
  }
  server_store.fetch_server_list().catch((error) => console.warn('fetch_server_list failed', error))
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('nav.dashboard') }}</h1>
        <p class="page-desc">{{ t('dashboard.dashboard_page_desc') }}</p>
      </div>
      <Badge :variant="connection_state === 'connected' ? 'success' : 'danger'">
        <span class="pulse-dot" :class="{ 'pulse-dot--on': connection_state === 'connected' }" />
        {{
          connection_state === 'connected'
            ? t('dashboard.dashboard_ws_connected')
            : t('dashboard.dashboard_ws_disconnected')
        }}
      </Badge>
    </div>

    <!-- 状态条 -->
    <section class="stats-strip card">
      <div v-for="item in stat_items" :key="item.label" class="stat-cell">
        <Icon :icon="item.icon" width="16" class="stat-icon" />
        <div class="stat-body">
          <span class="stat-value">{{ item.value }}</span>
          <span class="stat-label">{{ item.label }}</span>
        </div>
      </div>
      <div class="stat-cell">
        <Icon icon="lucide:memory-stick" width="16" class="stat-icon" />
        <div class="stat-body stat-body--wide">
          <span class="stat-value">{{ format_mb(status?.memory_mb) }}</span>
          <Progress :value="memory_percent" />
          <span class="stat-label">{{ t('dashboard.dashboard_stat_memory') }}</span>
        </div>
      </div>
      <div class="stat-cell">
        <Icon icon="lucide:gauge" width="16" class="stat-icon" />
        <div class="stat-body stat-body--wide">
          <span class="stat-value">{{ status?.cpu_percent ?? '—' }}%</span>
          <Progress :value="status?.cpu_percent || 0" />
          <span class="stat-label">{{ t('dashboard.dashboard_stat_cpu') }}</span>
        </div>
      </div>
    </section>

    <!-- 快速开始引导 -->
    <SetupGuide />

    <div class="dashboard-grid">
      <!-- 服务器一览 -->
      <section class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('dashboard.dashboard_server_title') }}</h3>
          <Badge variant="accent">
            {{
              t('dashboard.dashboard_server_online_count', {
                online: online_count,
                total: server_list.length,
              })
            }}
          </Badge>
        </div>
        <div class="card-body server-panel">
          <EmptyState
            v-if="server_list.length === 0"
            icon="lucide:server-off"
            :title="t('dashboard.dashboard_server_empty_title')"
            :description="t('dashboard.dashboard_server_empty_description')"
          />
          <ul v-else class="server-rows">
            <li
              v-for="server in server_list"
              :key="server.name"
              class="server-row"
              @click="router.push(`/servers/${server.name}`)"
            >
              <Icon
                class="server-type-icon"
                :icon="server_type_icon(server.server_type)"
                width="15"
                :title="server_type_label(server.server_type)"
              />
              <span
                class="server-dot"
                :class="server.online ? 'server-dot--on' : 'server-dot--off'"
              />
              <div class="server-info">
                <span class="server-name">{{ server.name }}</span>
                <span class="server-motd">{{ server.motd || '—' }}</span>
              </div>
              <div class="server-meta">
                <Badge :variant="server.online ? 'success' : 'neutral'">
                  {{ server.online ? t('common.online') : t('common.offline') }}
                </Badge>
                <span class="server-players">
                  <Icon icon="lucide:users" width="13" />
                  {{ server.players }} / {{ server.max_players }}
                </span>
              </div>
              <Icon icon="lucide:chevron-right" width="15" class="text-muted" />
            </li>
          </ul>
        </div>
      </section>

      <!-- 实时日志 -->
      <section class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('dashboard.dashboard_logs_title') }}</h3>
          <RouterLink to="/logs" class="more-link">
            {{ t('dashboard.dashboard_logs_view_all') }}
            <Icon icon="lucide:arrow-right" width="13" />
          </RouterLink>
        </div>
        <div class="log-stream">
          <div v-if="display_logs.length === 0" class="log-placeholder">
            {{ t('dashboard.dashboard_logs_waiting') }}
          </div>
          <div
            v-for="(log, index) in display_logs"
            :key="log.seq || `${log.time}-${index}`"
            class="log-row"
          >
            <!-- 新推送带 ANSI 彩色行：整行渲染（含级别颜色与模块名天蓝下划线） -->
            <template v-if="log.ansi">
              <span class="log-ansi" v-html="cached_ansi_html(log, is_dark)" />
            </template>
            <!-- 旧缓存无 ANSI：回退分列渲染 -->
            <template v-else>
              <span class="log-time mono">{{ log.time }}</span>
              <span class="log-level mono" :class="level_class(log.level)">
                {{ log.level || '—' }}
              </span>
              <span class="log-message">{{ log.message }}</span>
            </template>
          </div>
        </div>
      </section>
    </div>

    <!-- 适配器 -->
    <section class="card adapter-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('dashboard.dashboard_adapters_title') }}</h3>
      </div>
      <div class="card-body adapter-list">
        <Badge v-for="adapter in status?.adapters || []" :key="adapter" variant="neutral">
          <Icon icon="lucide:plug" width="12" />
          {{ adapter }}
        </Badge>
        <span v-if="!status?.adapters?.length" class="text-muted text-sm">
          {{ t('dashboard.dashboard_adapters_empty') }}
        </span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.pulse-dot--on {
  animation: pulse 1.6s ease-out infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, currentColor 50%, transparent);
  }
  100% {
    box-shadow: 0 0 0 5px transparent;
  }
}

/* 状态条 */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  margin-bottom: var(--space-5);
}

.stat-cell {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  min-width: 0;
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

.stat-body--wide {
  flex: 1;
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

/* 双栏 */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

/* 防止 nowrap 内容（MOTD 等）把 1fr 轨道撑到 min-content 导致整页横向溢出 */
.dashboard-grid > .card {
  min-width: 0;
}

/* 服务器行 */
.server-panel {
  padding: 0;
}

.server-rows {
  display: flex;
  flex-direction: column;
}

.server-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background-color var(--transition);
}

.server-row:last-child {
  border-bottom: none;
}

.server-row:hover {
  background: var(--hover);
}

.server-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.server-type-icon {
  flex-shrink: 0;
  color: var(--text-muted);
}

.server-dot--on {
  background: var(--success);
}

.server-dot--off {
  background: var(--border-strong);
}

.server-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.server-name {
  font-size: var(--text-sm);
  font-weight: 600;
}

.server-motd {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.server-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.server-players {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* 日志流 */
.log-stream {
  height: 320px;
  overflow-y: auto;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sunken);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.log-placeholder {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
}

.log-row {
  display: flex;
  gap: var(--space-3);
  padding: 3px 0;
  line-height: 1.6;
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-level {
  width: 56px;
  flex-shrink: 0;
  font-weight: 600;
}

.log-message {
  color: var(--text-secondary);
  word-break: break-all;
}

.log-ansi {
  word-break: break-all;
  white-space: pre-wrap;
}

.more-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--accent);
}

/* 适配器 */
.adapter-list {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

@media (max-width: 1100px) {
  .stats-strip {
    grid-template-columns: repeat(3, 1fr);
  }

  .stat-cell:nth-child(4) {
    border-left: none;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
