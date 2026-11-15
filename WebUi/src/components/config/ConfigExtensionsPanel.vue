<script setup>
/**
 * 配置中心：扩展配置面板。
 *
 * 自包含「扩展条目导航 + 当前扩展配置表单 + 撤销/保存」。与 Config.toml 面板的差别：
 * 扩展配置没有本地基准值副本，草稿完全由 SchemaForm 内部维护，改动数经 `change`
 * 事件同步，保存经 `save` 事件回传序列化后的整表值。挂载时按需拉取可配置扩展清单。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useExtensionStore } from '@/stores/extension'
import { use_toast } from '@/composables/use_toast'
import { use_extension_labels } from '@/composables/use_extension_labels'
import Badge from '@/components/ui/Badge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import SchemaForm from '@/components/ui/SchemaForm.vue'
import ConfigGroupNav from '@/components/config/ConfigGroupNav.vue'
import ConfigTabActions from '@/components/config/ConfigTabActions.vue'

/** 当前选中的扩展 id（父级持有以同步 URL query） */
const active_extension_id = defineModel({ type: String, default: '' })

const { t } = useI18n()
const extension_store = useExtensionStore()
const toast = use_toast()
// 类型 / 状态显示名与徽标变体由公共 composable 提供，避免与扩展管理页各写一份映射
const { type_label, state_label, state_variant } = use_extension_labels()
const { config_items, config_items_loading, saving_config_item } = storeToRefs(extension_store)

/** 扩展配置是否已尝试加载（避免首帧误显示空状态） */
const extensions_loaded = ref(false)
/** 当前扩展配置的改动字段数量（由表单 change 事件同步） */
const changes_count = ref(0)
/** 有改动的扩展 id 集合（用于导航黄点） */
const changed_ids = computed(
  () => new Set(changes_count.value > 0 ? [active_extension_id.value] : []),
)
const form_ref = ref(null)

/** 有配置项的扩展列表（代码扩展 + 无代码模板包） */
const extension_items = computed(() => config_items.value)

/** 当前选中的扩展配置项 */
const active_extension_item = computed(
  () => extension_items.value.find((item) => item.id === active_extension_id.value) || null,
)

/** 选中首个扩展（优先父级经 URL query 传入的 id，无效则回退第一项） */
function select_default(preferred_id) {
  const matched =
    typeof preferred_id === 'string' &&
    preferred_id !== '' &&
    extension_items.value.some((item) => item.id === preferred_id)
  active_extension_id.value = matched ? preferred_id : extension_items.value[0].id
}

onMounted(async () => {
  if (extension_items.value.length > 0) {
    extensions_loaded.value = true
    if (!active_extension_item.value) select_default(active_extension_id.value)
    return
  }
  try {
    await extension_store.fetch_config_items()
    if (extension_items.value.length > 0) select_default(active_extension_id.value)
  } catch (error) {
    toast.error(error.message || t('config_view.toast_load_extensions_failed'))
  } finally {
    extensions_loaded.value = true
  }
})

async function save_item(item, values) {
  try {
    await extension_store.save_config_item(item.id, values)
    toast.success(t('extensions.config_save_success', { name: item.name }))
    // store 刷新后 values 已是新值，等一次渲染再重建草稿清除改动计数
    await nextTick()
    form_ref.value?.reset_draft()
  } catch (error) {
    toast.error(error.message || t('extensions.config_save_failed'))
  }
}

function revert_changes() {
  form_ref.value?.reset_draft()
}

// 切换扩展时表单会重建，先清零计数避免操作栏闪出上一项的改动数
watch(active_extension_id, () => {
  changes_count.value = 0
})
</script>

<template>
  <div>
    <ConfigTabActions
      :change-count="changes_count"
      :saving="saving_config_item === active_extension_id"
      @revert="revert_changes"
      @save="form_ref?.confirm_save()"
    >
      <template #left>
        <span class="text-xs text-muted">{{ t('config_view.tab_extensions_hint') }}</span>
      </template>
    </ConfigTabActions>

    <div v-if="config_items_loading || !extensions_loaded" class="card">
      <div class="loading-block">
        <Spinner :size="18" /> {{ t('config_view.tab_extensions_loading') }}
      </div>
    </div>

    <EmptyState
      v-else-if="extension_items.length === 0"
      icon="lucide:puzzle"
      :title="t('config_view.tab_extensions_empty_title')"
      :description="t('config_view.tab_extensions_empty_description')"
    />

    <div v-else class="config-layout">
      <ConfigGroupNav
        :items="extension_items"
        :active-id="active_extension_id"
        :changed-ids="changed_ids"
        @select="(id) => (active_extension_id = id)"
      />

      <section v-if="active_extension_item" class="card config-panel">
        <div class="card-header extension-panel-header">
          <div class="extension-panel-title">
            <div class="extension-panel-title-line">
              <h3 class="card-title">{{ active_extension_item.name }}</h3>
              <span class="mono text-muted">{{ active_extension_item.id }}</span>
            </div>
            <p v-if="active_extension_item.description" class="extension-panel-desc">
              {{ active_extension_item.description }}
            </p>
          </div>
          <div class="extension-panel-badges">
            <Badge v-for="type in active_extension_item.types || []" :key="type" variant="accent">
              {{ type_label(type) }}
            </Badge>
            <Badge :variant="state_variant(active_extension_item.state)">
              {{ state_label(active_extension_item.state) }}
            </Badge>
          </div>
        </div>
        <div class="extension-panel-form">
          <SchemaForm
            ref="form_ref"
            :key="active_extension_item.id"
            :schema="active_extension_item.schema"
            :values="active_extension_item.values"
            :saving="saving_config_item === active_extension_item.id"
            :show-actions="false"
            :keep-draft-on-schema-change="true"
            @change="(count) => (changes_count = count)"
            @save="(values) => save_item(active_extension_item, values)"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.config-layout {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: var(--space-5);
  align-items: start;
}

/* 扩展配置面板头部 */
.extension-panel-header {
  align-items: flex-start;
  gap: var(--space-3);
}

/* 标题区：名称 / ID 一行，描述紧随其下（均位于头部左侧栏） */
.extension-panel-title {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.extension-panel-title-line {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  min-width: 0;
}

.extension-panel-title .card-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.extension-panel-badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-1);
}

.extension-panel-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

.extension-panel-form {
  padding: var(--space-2) var(--space-4) var(--space-5);
}

@media (max-width: 900px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
}
</style>
