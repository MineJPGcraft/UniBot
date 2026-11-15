<!-- 通用市场面板：搜索工具栏 + 卡片网格 + 分页，供插件市场 / 扩展市场复用 -->
<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Pagination from '@/components/ui/Pagination.vue'

const props = defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  /** 为空时回退到模块默认文案 */
  placeholder: { type: String, default: '' },
  /** 工具栏右侧提示文案，为空则不显示 */
  hint: { type: String, default: '' },
  emptyTitle: { type: String, default: '' },
  emptyDescription: { type: String, default: '' },
  /** 分页配置；total 为 0 时不显示分页 */
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  /** 卡片图标（Iconify），默认插件图标 */
  itemIcon: { type: String, default: 'lucide:puzzle' },
  /** 当前操作中的条目 key，用于按钮 loading 与全局禁用 */
  busy: { type: String, default: '' },
  /** 是否显示安装 / 升级操作按钮（权限控制） */
  showActions: { type: Boolean, default: true },
  /** 是否启用多版本切换（扩展市场专用，需后端提供版本清单接口） */
  versionSwitch: { type: Boolean, default: false },
  /** 当前打开版本菜单的条目 key */
  releasesFor: { type: String, default: '' },
  /** 正在加载版本清单的条目 key */
  releasesLoading: { type: String, default: '' },
  /** 当前条目可选版本：[{ version, compatible, installed }]，按版本倒序 */
  releases: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'update:model-value',
  'search',
  'page-change',
  'install',
  'upgrade',
  'open-releases',
  'install-version',
])

const { t } = useI18n()

const search_placeholder = computed(
  () => props.placeholder || t('extensions.market_search_placeholder'),
)
const empty_title_text = computed(() => props.emptyTitle || t('extensions.market_empty_title'))
const empty_description_text = computed(
  () => props.emptyDescription || t('extensions.market_empty_description'),
)

/** 版本切换菜单项（扩展市场专用，按版本倒序） */
const release_items = computed(() => {
  if (props.releasesLoading === props.releasesFor) {
    return [{ label: t('extensions.market_versions_loading'), disabled: true }]
  }
  if (props.releases.length === 0) {
    return [{ label: t('extensions.market_versions_empty'), disabled: true }]
  }
  return props.releases.map((release) => ({
    label: release.compatible
      ? t('extensions.market_version_name', { version: release.version })
      : t('extensions.market_version_incompatible_name', { version: release.version }),
    icon: release.installed
      ? 'lucide:check'
      : release.compatible
        ? 'lucide:tag'
        : 'lucide:shield-alert',
    disabled: !release.compatible || release.installed || Boolean(props.busy),
    on_select: () => install_version(release.version),
  }))
})

function item_key(item) {
  return item.module_name || item.id || item.project_link || ''
}

function is_official(item) {
  return Boolean(item.official || item.is_official)
}

function item_desc(item) {
  return item.description || item.desc || t('extensions.market_no_description')
}

function item_version(item) {
  return item.latest_version || item.version
}

/** 默认安装目标版本：有兼容历史版本时用 target_version（扩展市场），否则回退最新版本 */
function target_version(item) {
  return item.target_version || item_version(item)
}

/** 是否没有任何兼容当前核心版本的发布（仅扩展市场会带 compatible 字段） */
function is_unsupported(item) {
  return item.compatible === false
}

/** 扩展市场：最新版本不兼容、将安装历史兼容版本 */
function has_fallback(item) {
  return Boolean(item.has_compatible_fallback)
}

/** 项目仓库地址（owner/repo），为空时返回空字符串 */
function repo_url(item) {
  return item.repo ? `https://github.com/${item.repo}` : ''
}

/** 项目主页地址：优先 homepage，其次由 repo 拼出 GitHub 地址，都没有返回空 */
function project_url(item) {
  return item.homepage || repo_url(item)
}

/** 仓库地址第一段为作者名（owner），无 repo 时回退到 item.repo 原值 */
function repo_author(item) {
  if (!item.repo) return ''
  return String(item.repo).split('/')[0] || item.repo
}

/** 版本号是否一致（容忍 v 前缀差异，仅用于更新判断，不影响显示） */
function same_version(a, b) {
  return String(a).replace(/^v/i, '') === String(b).replace(/^v/i, '')
}

/**
 * 是否有可用更新：
 * 插件市场带 registered 字段（无已安装版本数据，沿用原逻辑）；
 * 扩展市场比较已安装版本与「默认安装目标版本」（已自动避开不兼容的新版本）。
 */
function has_update(item) {
  if ('registered' in item) return true
  const { installed, installed_version } = item
  const target = target_version(item)
  if (!installed || !installed_version || !target) return false
  return !same_version(installed_version, target)
}

/**
 * 是否显示「升级」按钮：
 * 插件市场带 registered 字段（需已安装且已登记才可升级）；
 * 扩展市场无该字段，需已安装且有可用更新。
 */
function can_upgrade(item) {
  if ('registered' in item) return Boolean(item.installed && item.registered)
  return Boolean(item.installed && has_update(item))
}

function search() {
  emit('search')
}

function go_page(page) {
  emit('page-change', page)
}

function install(item) {
  emit('install', item)
}

function upgrade(item) {
  emit('upgrade', item)
}

function open_releases(item) {
  emit('open-releases', item)
}

function install_version(version) {
  emit('install-version', version)
}
</script>

<template>
  <div class="card market-panel">
    <form class="market-toolbar" @submit.prevent="search">
      <Input
        :model-value="modelValue"
        class="market-search"
        :placeholder="search_placeholder"
        @update:model-value="(value) => emit('update:model-value', value)"
        @keydown.enter="search"
      />
      <Button variant="secondary" type="submit" :loading="loading">
        <Icon icon="lucide:search" width="14" />
        {{ t('extensions.market_search') }}
      </Button>
      <p v-if="hint" class="market-hint">{{ hint }}</p>
    </form>

    <div v-if="loading" class="loading-block">
      <Spinner :size="18" /> {{ t('extensions.market_loading') }}
    </div>
    <EmptyState
      v-else-if="items.length === 0"
      icon="lucide:store"
      :title="empty_title_text"
      :description="empty_description_text"
    />
    <div v-else class="market-grid">
      <article v-for="item in items" :key="item_key(item)" class="market-card card">
        <div class="market-head">
          <div class="market-icon"><Icon :icon="itemIcon" width="18" /></div>
          <div class="market-title">
            <h3 class="market-item-title">
              {{ item.name }}
              <Badge v-if="is_official(item)" variant="success">
                {{ t('extensions.market_official_badge') }}
              </Badge>
            </h3>
            <span class="market-name mono">{{ item_key(item) }}</span>
          </div>
          <Badge v-if="item.installed" variant="neutral">
            {{ t('extensions.market_installed_badge') }}
          </Badge>
          <Badge v-else-if="item.registered" variant="warning">
            {{ t('extensions.market_registered_badge') }}
          </Badge>
          <Badge v-else-if="is_unsupported(item)" variant="danger">
            <Icon icon="lucide:shield-alert" width="11" />
            {{ t('extensions.market_unsupported_badge') }}
          </Badge>
        </div>

        <p class="market-desc">{{ item_desc(item) }}</p>

        <div v-if="item.tags && item.tags.length" class="market-tags">
          <span
            v-for="tag in item.tags.slice(0, 3)"
            :key="tag.label"
            class="market-tag"
            :style="tag.color ? { '--tag-color': tag.color } : {}"
          >
            {{ tag.label }}
          </span>
        </div>

        <div class="market-foot">
          <div class="market-meta">
            <span class="mono" :class="{ 'text-muted': is_unsupported(item) }">
              v{{ item_version(item) }}
            </span>
            <span
              v-if="has_fallback(item)"
              class="market-fallback"
              :title="t('extensions.market_fallback_tooltip')"
            >
              <Icon icon="lucide:arrow-right" width="11" />
              v{{ target_version(item) }}
            </span>
            <a
              v-if="item.repo"
              :href="repo_url(item)"
              target="_blank"
              rel="noopener noreferrer"
              class="market-author"
              :title="t('extensions.market_repo_tooltip')"
            >
              · {{ repo_author(item) }}
            </a>
            <span v-else-if="item.author" class="text-muted">· {{ item.author }}</span>
          </div>
          <div class="market-actions">
            <a
              v-if="project_url(item)"
              :href="project_url(item)"
              target="_blank"
              rel="noopener noreferrer"
              class="market-homepage"
              :title="
                item.homepage
                  ? t('extensions.market_homepage_tooltip')
                  : t('extensions.market_repo_tooltip')
              "
            >
              <Icon icon="lucide:github" width="15" />
            </a>
            <template v-if="showActions && versionSwitch">
              <DropdownMenu
                align="end"
                :items="releasesFor === item_key(item) ? release_items : []"
              >
                <template #trigger>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon-only
                    :title="t('extensions.market_version_switch_title')"
                    :disabled="Boolean(busy) || is_unsupported(item)"
                    @click="open_releases(item)"
                  >
                    <Icon
                      :icon="
                        releasesLoading === item_key(item) ? 'lucide:loader' : 'lucide:history'
                      "
                      width="14"
                    />
                  </Button>
                </template>
              </DropdownMenu>
            </template>
            <template v-if="showActions">
              <Button
                v-if="is_unsupported(item)"
                variant="secondary"
                size="sm"
                disabled
                :title="t('extensions.market_unsupported_tooltip')"
              >
                <Icon icon="lucide:shield-alert" width="13" />
                {{ t('extensions.market_unsupported_badge') }}
              </Button>
              <Button
                v-else-if="can_upgrade(item)"
                variant="secondary"
                size="sm"
                :loading="busy === item_key(item)"
                :disabled="Boolean(busy)"
                @click="upgrade(item)"
              >
                <Icon icon="lucide:refresh-cw" width="13" />
                {{ t('extensions.market_upgrade') }}
              </Button>
              <Button
                v-else-if="!item.installed"
                size="sm"
                :loading="busy === item_key(item)"
                :disabled="Boolean(busy)"
                @click="install(item)"
              >
                <Icon icon="lucide:download" width="13" />
                {{ t('extensions.market_install') }}
              </Button>
              <Button
                v-else
                variant="secondary"
                size="sm"
                disabled
                :title="t('extensions.market_up_to_date')"
              >
                <Icon icon="lucide:refresh-cw" width="13" />
                {{ t('extensions.market_upgrade') }}
              </Button>
            </template>
          </div>
        </div>
      </article>
    </div>

    <div v-if="total > pageSize" class="market-pagination">
      <Pagination :page="page" :page-size="pageSize" :total="total" @page-change="go_page" />
    </div>
  </div>
</template>

<style scoped>
.market-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}

.market-toolbar .market-search {
  width: 300px;
}

/* 工具栏右侧提示文案 */
.market-hint {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

.market-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
}

.market-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-3);
}

.market-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.market-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.market-title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.market-item-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
}

.market-name {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.market-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.market-tags {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.market-tag {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  background: color-mix(in srgb, var(--tag-color, #999) 14%, transparent);
  color: var(--tag-color, var(--text-muted));
}

.market-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}

.market-meta,
.market-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
}

.market-actions {
  gap: var(--space-2);
}

.market-homepage {
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

.market-homepage:hover {
  background: var(--hover);
  color: var(--text);
}

/* 最新版不兼容、将安装兼容历史版本的提示标记 */
.market-fallback {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 5px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--warning);
  background: var(--warning-soft);
}

.market-author {
  color: var(--text-muted);
  text-decoration: none;
  transition:
    color var(--transition),
    text-decoration-color var(--transition);
}

.market-author:hover {
  color: var(--accent);
  text-decoration: underline;
}

.market-pagination {
  display: flex;
  justify-content: center;
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border);
}
</style>
