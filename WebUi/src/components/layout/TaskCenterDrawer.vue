<script setup>
/**
 * 右上角任务中心抽屉：后台任务的进度、日志与操作。
 *
 * 标题与阶段说明由后端下发「消息键 + 参数」，此处按当前界面语言翻译，
 * 因此切换语言后历史任务文案也会同步更新。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useTaskStore } from '@/stores/task'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import { format_datetime } from '@/utils/format'
import {
  format_elapsed,
  is_active,
  kind_icon,
  status_label,
  status_variant,
  task_elapsed_seconds,
  task_message,
  task_title,
} from '@/utils/task'
import Drawer from '@/components/ui/Drawer.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Tooltip from '@/components/ui/Tooltip.vue'

const { t } = useI18n()
const toast = use_toast()
const task_store = useTaskStore()
const { active_count, sorted_items, loading, logs, selected_id } = storeToRefs(task_store)
const { run } = use_async_action()

const open = ref(false)
const filter = ref('all')
// 每秒自增，驱动「耗时」在运行中实时走动
const clock = ref(0)
let clock_timer = null

const FILTERS = computed(() => [
  { value: 'all', label: t('task_center.filter_all') },
  { value: 'active', label: t('task_center.filter_active') },
  { value: 'finished', label: t('task_center.filter_finished') },
])

const visible_items = computed(() => {
  if (filter.value === 'active') return sorted_items.value.filter((item) => is_active(item))
  if (filter.value === 'finished') return sorted_items.value.filter((item) => !is_active(item))
  return sorted_items.value
})

/** 运行时长文本；未结束的任务按当前时间实时计算 */
function elapsed_text(task) {
  clock.value
  return format_elapsed(task_elapsed_seconds(task))
}

function created_text(task) {
  if (!task.created_at) return ''
  return format_datetime(new Date(task.created_at * 1000).toISOString())
}

function is_selected(task) {
  return selected_id.value === task.id
}

function toggle_detail(task) {
  if (is_selected(task)) {
    task_store.clear_selection()
    return
  }
  task_store.select(task.id)
}

async function cancel_task(task) {
  const ok = await run(() => task_store.cancel_task(task.id), t('common.operation_failed'))
  if (ok) toast.success(t('task_center.cancel_success'))
}

async function retry_task(task) {
  const ok = await run(() => task_store.retry_task(task.id), t('common.operation_failed'))
  if (ok) toast.success(t('task_center.retry_success'))
}

async function sync_dependencies() {
  const ok = await run(() => task_store.sync_dependencies(), t('common.operation_failed'))
  if (ok) {
    toast.success(t('task_center.sync_submitted'))
    filter.value = 'all'
  }
}

/** 打开 Studio 结果里给出的地址（任务 result.url） */
function open_studio_result(task) {
  if (task.result?.url) window.open(task.result.url, '_blank', 'noopener')
}

/**
 * 运行中任务的「耗时」需要实时走动，但只在抽屉打开时才需要：
 * 抽屉关闭时停掉计时器，避免全局常驻的每秒组件更新。
 */
watch(open, (value) => {
  if (value) {
    task_store.fetch_tasks().catch((error) => console.warn('fetch_tasks failed', error))
    start_clock()
  } else {
    stop_clock()
  }
})

function start_clock() {
  if (clock_timer) return
  clock_timer = setInterval(() => {
    clock.value += 1
  }, 1000)
}

function stop_clock() {
  if (!clock_timer) return
  clearInterval(clock_timer)
  clock_timer = null
}

onMounted(() => {
  task_store.init()
  task_store.fetch_tasks().catch((error) => console.warn('fetch_tasks failed', error))
})

onUnmounted(() => {
  stop_clock()
  task_store.dispose()
})
</script>

<template>
  <!-- 不用 Drawer 的 #trigger 插槽：reka 的 DrawerTrigger(as-child) 会把 click 等属性合并到
       插槽第一个节点上，而这里第一个节点是 Tooltip 组件——组件若以 Fragment 为根
       （TooltipRoot → PopperRoot 只 renderSlot），透传属性会被丢弃，点击就不会打开抽屉。
       改为自己控制 open，Tooltip 与按钮的关系和顶栏其它按钮保持一致。 -->
  <Tooltip :text="t('task_center.trigger_hint')">
    <button class="task-trigger" @click="open = true">
      <Icon icon="lucide:list-todo" width="16" />
      <span v-if="active_count > 0" class="task-trigger-count">{{ active_count }}</span>
    </button>
  </Tooltip>

  <Drawer
    v-model="open"
    :title="t('task_center.title')"
    :description="t('task_center.description')"
    direction="right"
  >
    <div class="task-toolbar">
      <div class="task-filters">
        <button
          v-for="item in FILTERS"
          :key="item.value"
          class="task-filter"
          :class="{ 'task-filter--active': filter === item.value }"
          @click="filter = item.value"
        >
          {{ item.label }}
        </button>
      </div>
      <Button variant="ghost" size="xs" :loading="loading" @click="sync_dependencies">
        <Icon icon="lucide:package-search" width="14" />
        {{ t('task_center.sync_dependencies') }}
      </Button>
    </div>

    <EmptyState
      v-if="visible_items.length === 0"
      icon="lucide:list-todo"
      :title="t('task_center.empty')"
      :description="t('task_center.empty_hint')"
    />

    <ul v-else class="task-list">
      <li v-for="task in visible_items" :key="task.id" class="task-item">
        <button class="task-row" @click="toggle_detail(task)">
          <span class="task-icon" :class="`task-icon--${task.status}`">
            <Icon :icon="kind_icon(task.kind)" width="16" />
          </span>
          <span class="task-main">
            <span class="task-head">
              <span class="task-title">{{ task_title(task) }}</span>
              <Badge :variant="status_variant(task.status)">
                {{ status_label(task.status) }}
              </Badge>
            </span>
            <span class="task-message">{{ task_message(task) }}</span>
            <span class="task-meta">
              <span>{{ created_text(task) }}</span>
              <span v-if="elapsed_text(task)">{{
                t('task_center.elapsed', { duration: elapsed_text(task) })
              }}</span>
            </span>
            <Progress v-if="is_active(task)" :value="task.progress || 0" />
          </span>
          <Icon
            :icon="is_selected(task) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
            width="14"
            class="task-caret"
          />
        </button>

        <div v-if="is_selected(task)" class="task-detail">
          <div v-if="task.error" class="task-error">{{ task.error }}</div>
          <div v-if="task.result?.url" class="task-result">
            <Button variant="secondary" size="xs" @click="open_studio_result(task)">
              <Icon icon="lucide:external-link" width="14" />
              {{ t('task_center.open_studio') }}
            </Button>
          </div>
          <div class="task-logs-head">{{ t('task_center.logs_title') }}</div>
          <pre v-if="logs.length" class="task-logs">{{ logs.join('\n') }}</pre>
          <div v-else class="task-logs-empty">{{ t('task_center.logs_empty') }}</div>
          <div class="task-actions">
            <Button v-if="is_active(task)" variant="danger" size="xs" @click="cancel_task(task)">
              <Icon icon="lucide:x" width="14" />
              {{ t('task_center.cancel') }}
            </Button>
            <Button
              v-else-if="task.retryable"
              variant="secondary"
              size="xs"
              @click="retry_task(task)"
            >
              <Icon icon="lucide:rotate-ccw" width="14" />
              {{ t('task_center.retry') }}
            </Button>
          </div>
        </div>
      </li>
    </ul>
  </Drawer>
</template>

<style scoped>
.task-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius);
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.task-trigger:hover {
  background: var(--hover);
  color: var(--text);
}

.task-trigger-count {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--accent);
  color: #ffffff;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
}

.task-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.task-filters {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.task-filter {
  height: 24px;
  padding: 0 var(--space-2);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.task-filter:hover {
  background: var(--hover);
  color: var(--text);
}

.task-filter--active {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.task-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  overflow: hidden;
}

.task-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3);
  text-align: left;
  transition: background-color var(--transition);
}

.task-row:hover {
  background: var(--hover);
}

.task-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text-muted);
}

.task-icon--running {
  background: var(--accent-soft);
  color: var(--accent);
}

.task-icon--succeeded {
  background: var(--success-soft);
  color: var(--success);
}

.task-icon--failed {
  background: var(--danger-soft);
  color: var(--danger);
}

.task-icon--cancelled {
  background: var(--warning-soft);
  color: var(--warning);
}

.task-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
  min-width: 0;
}

.task-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.task-title {
  font-size: var(--text-sm);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-message {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.task-caret {
  flex-shrink: 0;
  margin-top: var(--space-2);
  color: var(--text-muted);
}

.task-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--border);
  background: var(--surface-sunken);
}

.task-error {
  padding: var(--space-2);
  border-radius: var(--radius);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.task-result {
  display: flex;
  justify-content: flex-start;
}

.task-logs-head {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
}

.task-logs {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  padding: var(--space-2);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--text) 4%, transparent);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.task-logs-empty {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.task-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
