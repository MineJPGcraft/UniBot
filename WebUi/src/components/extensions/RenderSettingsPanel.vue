<script setup>
/**
 * 扩展管理：渲染设置面板。
 *
 * 三段内容：图片渲染引擎选择、模板选择、各渲染插件 / 模板包的配置表单。
 * 图片模式（`image.mode`）关闭时整面板锁定并显示提示横幅；渲染插件与模板的配置
 * 表单共用 SchemaForm，字段语义由 utils/schema_form.js 判定。
 */
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useExtensionStore } from '@/stores/extension'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'
import Badge from '@/components/ui/Badge.vue'
import Select from '@/components/ui/Select.vue'
import Spinner from '@/components/ui/Spinner.vue'
import SchemaForm from '@/components/ui/SchemaForm.vue'

const { t } = useI18n()
const extension_store = useExtensionStore()
const auth_store = useAuthStore()
const config_store = useConfigStore()
const toast = use_toast()
const { ask_restart } = use_restart()
const {
  renderers,
  renderer_loading,
  templates,
  template_loading,
  render_configs,
  render_config_loading,
  saving_render_config,
} = storeToRefs(extension_store)

/** 图片模式是否开启；关闭时「渲染设置」整体锁定 */
const image_mode_enabled = computed(() => Boolean(config_store.config_data?.image?.mode))

const current_renderer = computed(() => {
  const matched = renderers.value.find((item) => item.current)
  return (matched || {}).name || ''
})

/** 引擎下拉只列当前可用的渲染插件 */
const renderer_options = computed(() =>
  renderers.value
    .filter((item) => item.available)
    .map((item) => ({ value: item.name, label: item.name })),
)

const current_template = computed(
  () => (templates.value.find((item) => item.current) || templates.value[0] || {}).name || '',
)

const template_options = computed(() =>
  templates.value.map((item) => ({
    value: item.name,
    label: item.name || t('extensions.template_default_option'),
  })),
)

/** 只展示带配置项的渲染插件 / 模板包 */
const visible_render_configs = computed(() =>
  render_configs.value.filter((item) => {
    const properties = item.schema?.properties || {}
    return Object.keys(properties).length > 0
  }),
)

async function change_renderer(name) {
  try {
    await extension_store.switch_renderer(name)
    toast.success(t('extensions.renderer_switch_success'))
    ask_restart(t('extensions.renderer_switch_restart_prompt'))
  } catch (error) {
    toast.error(error.message || t('extensions.renderer_switch_failed'))
  }
}

async function change_template(name) {
  try {
    await extension_store.switch_template(name)
    toast.success(t('extensions.template_switch_success'))
  } catch (error) {
    toast.error(error.message || t('extensions.template_switch_failed'))
  }
}

async function save_render_plugin_config(item, values) {
  try {
    await extension_store.save_render_config(item.id, values)
    toast.success(t('extensions.config_save_success', { name: item.name }))
  } catch (error) {
    toast.error(error.message || t('extensions.config_save_failed'))
  }
}
</script>

<template>
  <div class="render-panel card">
    <div v-if="!image_mode_enabled" class="render-lock-banner">
      <Icon icon="lucide:lock" width="14" />
      {{ t('extensions.render_lock_banner') }}
    </div>

    <div class="render-row">
      <div class="render-meta">
        <h3 class="card-title">{{ t('extensions.renderer_section_title') }}</h3>
        <p class="render-desc">{{ t('extensions.renderer_section_desc') }}</p>
      </div>
      <div v-if="renderer_loading" class="render-loading"><Spinner :size="16" /></div>
      <Select
        v-else
        :model-value="current_renderer"
        :options="renderer_options"
        :disabled="!auth_store.is_admin || !image_mode_enabled"
        @update:model-value="change_renderer"
      />
    </div>

    <div class="render-row">
      <div class="render-meta">
        <h3 class="card-title">{{ t('extensions.template_section_title') }}</h3>
        <p class="render-desc">{{ t('extensions.template_section_desc') }}</p>
      </div>
      <div v-if="template_loading" class="render-loading"><Spinner :size="16" /></div>
      <Select
        v-else
        :model-value="current_template"
        :options="template_options"
        :disabled="!auth_store.is_admin || !image_mode_enabled"
        @update:model-value="change_template"
      />
    </div>

    <div class="render-row render-row--list">
      <div class="render-meta">
        <h3 class="card-title">{{ t('extensions.render_plugin_config_title') }}</h3>
        <p class="render-desc">{{ t('extensions.render_plugin_config_desc') }}</p>
      </div>
    </div>
    <div v-if="render_config_loading" class="render-config-loading">
      <Spinner :size="16" /> {{ t('extensions.render_config_loading') }}
    </div>
    <div v-else class="render-configs">
      <div
        v-for="item in visible_render_configs"
        :key="item.id"
        class="render-config-card"
        :class="{ 'render-config-card--unavailable': !item.available }"
      >
        <div class="render-config-head">
          <div class="render-config-title">
            <span class="render-config-kind" :class="`render-config-kind--${item.kind}`">
              <Icon
                :icon="item.kind === 'renderer' ? 'lucide:image' : 'lucide:layout-template'"
                width="14"
              />
            </span>
            <span class="render-config-name">{{ item.name }}</span>
            <Badge variant="neutral">
              <Icon icon="lucide:boxes" width="11" />
              {{
                item.kind === 'renderer'
                  ? t('extensions.renderer_kind_badge')
                  : t('extensions.template_kind_badge')
              }}
            </Badge>
            <Badge :variant="item.available ? 'success' : 'neutral'">
              <Icon
                :icon="item.available ? 'lucide:circle-check' : 'lucide:circle-off'"
                width="11"
              />
              {{
                item.available
                  ? t('extensions.renderer_status_available')
                  : t('extensions.renderer_status_unavailable')
              }}
            </Badge>
            <Badge v-if="item.current" variant="accent">
              <Icon icon="lucide:star" width="11" />
              {{ t('extensions.render_current_badge') }}
            </Badge>
          </div>
          <span v-if="!item.available && item.reason" class="renderer-item-reason">
            {{ item.reason }}
          </span>
        </div>
        <SchemaForm
          :schema="item.schema"
          :values="item.values"
          :saving="saving_render_config === item.id"
          :disabled="!item.available"
          :keep-draft-on-schema-change="true"
          @save="(values) => save_render_plugin_config(item, values)"
        />
      </div>
      <div v-if="!visible_render_configs.length" class="render-config-empty">
        {{ t('extensions.render_plugin_empty') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.render-panel {
  padding: 0 var(--space-5);
}

/* 图片模式未开启时的提示横幅 */
.render-lock-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid color-mix(in srgb, var(--warning) 40%, transparent);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--warning) 8%, transparent);
  color: var(--warning);
  font-size: var(--text-xs);
}

.render-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border);
}

.render-row:last-child {
  border-bottom: none;
}

.render-meta {
  flex: 1;
  min-width: 0;
}

.render-desc {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.render-loading {
  display: flex;
  align-items: center;
}

.render-row--list {
  align-items: flex-start;
}

.render-config-loading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: center;
  padding: var(--space-6) 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.render-configs {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) 0;
}

.render-config-card {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-elevated);
}

.render-config-card--unavailable {
  background: var(--bg-base);
}

.render-config-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--space-3);
}

.render-config-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.render-config-kind {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.render-config-kind--template {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  color: var(--accent);
}

.render-config-kind--renderer {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
}

.render-config-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-all;
}

.renderer-item-reason {
  font-size: var(--text-xs);
  color: var(--warning);
  line-height: 1.4;
}

.render-config-empty {
  padding: var(--space-6) 0;
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.render-panel :deep(.ui-select-trigger) {
  width: 220px;
}
</style>
