<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useLogStore } from '@/stores/log'
import { use_async_action } from '@/composables/use_async_action'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Badge from '@/components/ui/Badge.vue'
import Pagination from '@/components/ui/Pagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { format_bytes, format_datetime, level_class } from '@/utils/format'
import { cached_ansi_html } from '@/utils/ansi'
import { useThemeStore } from '@/stores/theme'

const log_store = useLogStore()
const { run } = use_async_action()
const { t } = useI18n()
const { is_dark } = storeToRefs(useThemeStore())
const {
  file_list,
  current_file,
  log_items,
  total,
  page,
  page_size,
  level_filter,
  keyword_filter,
  loading,
  live_logs,
  live_version,
} = storeToRefs(log_store)

const active_tab = ref('realtime') // history | realtime
const keyword_input = ref('')
const auto_scroll = ref(true)
const live_container = ref(null)

const level_options = computed(() => [
  { value: 'all', label: t('logs.level_all') },
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'SUCCESS', label: 'SUCCESS' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
])

const live_level_filter = ref('all')
const filtered_live_logs = computed(() => {
  if (!live_level_filter.value || live_level_filter.value === 'all') return live_logs.value
  return live_logs.value.filter((log) => log.level === live_level_filter.value)
})

// 共享缓存收到新日志时自动滚到底部
// （store 用 live_version 计数器通知，watch 数组 ref 的 push 不会触发）
watch(live_version, () => {
  if (auto_scroll.value) scroll_to_bottom()
})

// 切到实时日志 tab 时，将已有日志滚到底部
watch(active_tab, (tab) => {
  if (tab === 'realtime') scroll_to_bottom()
})

function scroll_to_bottom() {
  nextTick(() => {
    if (live_container.value) {
      live_container.value.scrollTop = live_container.value.scrollHeight
    }
  })
}

onMounted(async () => {
  // 实时日志由共享 store 缓存，跨页面保留；此处只需确保订阅已启动
  log_store.init_live()

  await run(async () => {
    await log_store.fetch_file_list()
    if (file_list.value.length > 0) {
      log_store.select_file(file_list.value[0].name)
      await log_store.fetch_content()
    }
  }, t('logs.fetch_failed'))
})

async function select_file(name) {
  log_store.select_file(name)
  keyword_input.value = ''
  await run(() => log_store.fetch_content(), t('logs.read_failed'))
}

// 过滤与分页均为客户端计算（store 的 filtered_lines/log_items），
// 变更后无需重新请求文件内容
function apply_keyword() {
  log_store.set_keyword_filter(keyword_input.value.trim())
}

function change_level(level) {
  log_store.set_level_filter(level)
}

function handle_page_change(target_page) {
  log_store.set_page(target_page)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('logs.page_title') }}</h1>
        <p class="page-desc">{{ t('logs.page_description') }}</p>
      </div>
      <div class="page-actions">
        <div class="tab-switch">
          <button
            class="tab-item"
            :class="{ 'tab-item--active': active_tab === 'history' }"
            @click="active_tab = 'history'"
          >
            <Icon icon="lucide:file-text" width="14" />
            {{ t('logs.tab_history') }}
          </button>
          <button
            class="tab-item"
            :class="{ 'tab-item--active': active_tab === 'realtime' }"
            @click="active_tab = 'realtime'"
          >
            <Icon icon="lucide:radio" width="14" />
            {{ t('logs.tab_realtime') }}
            <span class="live-dot" />
          </button>
        </div>
      </div>
    </div>

    <!-- 历史日志 -->
    <div v-if="active_tab === 'history'" class="log-layout">
      <aside class="file-panel card">
        <div class="card-header">
          <h3 class="card-title">{{ t('logs.files_card_title') }}</h3>
          <Button variant="ghost" size="sm" icon-only @click="log_store.fetch_file_list()">
            <Icon icon="lucide:refresh-cw" width="13" />
          </Button>
        </div>
        <ul class="file-list">
          <li
            v-for="file in file_list"
            :key="file.name"
            class="file-item"
            :class="{ 'file-item--active': current_file === file.name }"
            @click="select_file(file.name)"
          >
            <Icon icon="lucide:file-text" width="14" class="file-icon" />
            <div class="file-info">
              <span class="file-name mono">{{ file.name }}</span>
              <span class="file-meta">
                {{ format_bytes(file.size) }} · {{ format_datetime(file.modified) }}
              </span>
            </div>
          </li>
          <li v-if="file_list.length === 0" class="file-empty">{{ t('logs.files_empty') }}</li>
        </ul>
      </aside>

      <section class="content-panel card">
        <div class="filter-bar">
          <Select
            :model-value="level_filter"
            :options="level_options"
            @update:model-value="change_level"
          />
          <form class="keyword-box" @submit.prevent="apply_keyword">
            <Input
              v-model="keyword_input"
              :placeholder="t('logs.keyword_placeholder')"
              @keydown.enter="apply_keyword"
            />
            <Button variant="secondary" size="sm" type="submit">{{
              t('logs.filter_action')
            }}</Button>
          </form>
          <span class="text-xs text-muted">{{ t('logs.total_lines', { count: total }) }}</span>
        </div>

        <div v-if="!current_file" class="content-empty">
          <EmptyState icon="lucide:file-text" :title="t('logs.select_file_hint')" />
        </div>
        <div v-else-if="loading" class="loading-block">
          <Spinner :size="18" /> {{ t('common.loading') }}
        </div>
        <div v-else-if="log_items.length === 0" class="content-empty">
          <EmptyState icon="lucide:search-x" :title="t('logs.no_matching_lines')" />
        </div>
        <div v-else class="log-content">
          <div v-for="item in log_items" :key="item.line" class="log-line">
            <span class="line-no">{{ item.line }}</span>
            <span class="log-time mono">{{ item.time }}</span>
            <span class="log-level mono" :class="level_class(item.level)">{{ item.level }}</span>
            <span class="log-message">
              <span class="log-module mono">{{ item.module }}</span>
              {{ item.message }}
            </span>
          </div>
        </div>

        <div v-if="total > 0" class="content-footer">
          <Pagination
            :page="page"
            :page-size="page_size"
            :total="total"
            @page-change="handle_page_change"
          />
        </div>
      </section>
    </div>

    <!-- 实时日志 -->
    <section v-else class="card realtime-panel">
      <div class="filter-bar">
        <Select v-model="live_level_filter" :options="level_options" />
        <button
          class="auto-scroll"
          :class="{ 'auto-scroll--on': auto_scroll }"
          @click="auto_scroll = !auto_scroll"
        >
          <Icon icon="lucide:arrow-down-to-line" width="13" />
          {{ auto_scroll ? t('logs.auto_scroll_on') : t('logs.auto_scroll_off') }}
        </button>
        <Button variant="ghost" size="sm" @click="log_store.clear_live()">{{
          t('logs.clear_action')
        }}</Button>
        <span class="text-xs text-muted">{{
          t('logs.received_count', { count: live_logs.length })
        }}</span>
      </div>
      <div ref="live_container" class="live-stream">
        <div v-if="filtered_live_logs.length === 0" class="live-empty">
          {{ t('logs.waiting_for_logs') }}
        </div>
        <div
          v-for="(log, index) in filtered_live_logs"
          :key="log.seq || `${log.time}-${index}`"
          class="log-line"
        >
          <!-- 新推送带 ANSI 彩色行：整行渲染（含级别颜色与模块名天蓝下划线） -->
          <template v-if="log.ansi">
            <span class="log-ansi" v-html="cached_ansi_html(log, is_dark)" />
          </template>
          <!-- 旧缓存无 ANSI：回退分列渲染 -->
          <template v-else>
            <span class="log-time mono">{{ log.time }}</span>
            <span class="log-level mono" :class="level_class(log.level)">{{ log.level }}</span>
            <span class="log-module mono">{{ log.module }}</span>
            <span class="log-message">{{ log.message }}</span>
          </template>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tab-switch {
  display: inline-flex;
  gap: var(--space-1);
  padding: var(--space-1);
  background: color-mix(in srgb, var(--text) 4%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 30px;
  padding: 0 var(--space-4);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.tab-item--active {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  animation: blink 1.5s ease-in-out infinite;
}

@keyframes blink {
  50% {
    opacity: 0.3;
  }
}

/* 双栏布局：卡片整体约占 80% 页面高度（100px 为页面标题区估算高度） */
.log-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-5);
  height: calc(80vh - 100px);
  min-height: 420px;
}

/* 卡片内部纵向排布，内容区自动撑满剩余高度 */
.file-panel,
.content-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.file-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-2);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color var(--transition);
}

.file-item:hover {
  background: var(--hover);
}

.file-item--active {
  background: var(--accent-soft);
}

.file-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.file-item--active .file-icon {
  color: var(--accent);
}

.file-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.file-empty {
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* 过滤栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

/* 实时日志面板：约占 80% 页面高度，内容区弹性撑满 */
.realtime-panel {
  display: flex;
  flex-direction: column;
  height: calc(80vh - 100px);
  min-height: 420px;
}

.keyword-box {
  display: flex;
  gap: var(--space-2);
  width: 260px;
}

.auto-scroll {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: var(--text-xs);
  color: var(--text-muted);
  transition:
    border-color var(--transition),
    color var(--transition);
}

.auto-scroll--on {
  border-color: var(--success);
  color: var(--success);
}

/* 日志内容：弹性占满卡片剩余高度 */
.log-content,
.live-stream {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sunken);
  /* 深色内容块贴合卡片底部时保留外框圆角，避免直角遮住圆角 */
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.7;
}

.content-empty {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 加载中同样占满内容区 */
.log-layout .loading-block,
.realtime-panel .loading-block {
  flex: 1;
  align-items: center;
  justify-content: center;
}

.log-line {
  display: flex;
  gap: var(--space-2);
  padding: 1px 0;
  /* 屏外日志行跳过布局与绘制（低成本虚拟化替代），
     同时限制重排影响范围，避免新日志把整个列表重新布局 */
  content-visibility: auto;
  contain-intrinsic-size: auto 20px;
}

.line-no {
  width: 32px;
  text-align: right;
  color: var(--border-strong);
  flex-shrink: 0;
  user-select: none;
}

.log-time {
  /* HH:mm 共 5 字符，固定宽度保证各列对齐 */
  width: 40px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-level {
  width: 55px;
  flex-shrink: 0;
  font-weight: 600;
}

.log-module {
  color: var(--text-muted);
}

.log-message {
  color: var(--text-secondary);
  word-break: break-all;
}

.log-ansi {
  word-break: break-all;
  white-space: pre-wrap;
}

.live-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
}

.content-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border);
  /* 与卡片外框底部圆角对齐 */
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

@media (max-width: 900px) {
  .log-layout {
    grid-template-columns: 1fr;
  }
}
</style>
