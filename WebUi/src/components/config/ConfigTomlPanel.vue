<script setup>
/**
 * 配置中心：Config.toml 面板。
 *
 * 自包含「分组导航 + 当前分组表单 + 门控锁定遮罩 + 撤销/保存 + 保存前 diff 预览」，
 * 保存后按改动字段决定是否询问重启，并在图片模式由关转开时引导下载依赖扩展。
 * 草稿与提交由 config store 承担；字段语义由 utils/schema_form.js 判定。
 */
import { computed, nextTick, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/config'
import { use_restart } from '@/composables/use_restart'
import { use_toast } from '@/composables/use_toast'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import SchemaForm from '@/components/ui/SchemaForm.vue'
import DiffPreviewDialog from '@/components/config/DiffPreviewDialog.vue'
import ConfigGroupNav from '@/components/config/ConfigGroupNav.vue'
import ConfigTabActions from '@/components/config/ConfigTabActions.vue'
import ConfigImageDepsDialog from '@/components/config/ConfigImageDepsDialog.vue'
import { get_nested } from '@/utils/format'

/** 改动这些字段后需要重启才生效 */
const RESTART_DEPENDENT_KEYS = ['image.mode']

const emit = defineEmits(['edit-source'])

const { t } = useI18n()
const config_store = useConfigStore()
const toast = use_toast()
const { ask_restart } = use_restart()
const { schema, groups, config_data, draft, loading, saving, changes, has_changes } =
  storeToRefs(config_store)

const active_group = ref('')
const diff_open = ref(false)
const form_ref = ref(null)
const image_deps_ref = ref(null)

/** 首次拿到分组后默认选中第一个 */
watch(
  groups,
  (value) => {
    if (!active_group.value && value.length > 0) active_group.value = value[0].id
  },
  { immediate: true },
)

/** 当前分组对象（含 keys / gated_by 等元信息） */
const active_group_data = computed(
  () =>
    groups.value.find(
      (group) => group.id === active_group.value || group.name === active_group.value,
    ) || { keys: [] },
)

/** 当前分组显示名 */
const active_group_name = computed(() => active_group_data.value.name || active_group.value)

/** 已变更字段 key 集合（Set 查找，避免模板里嵌套 some 的 O(n²) 比较） */
const changed_keys = computed(() => new Set(changes.value.map((change) => change.key)))

/** 门控开关的草稿值（如 image.mode） */
const gate_value = computed(() => {
  const gate_key = active_group_data.value.gated_by
  return gate_key ? get_nested(draft.value, gate_key) : undefined
})

/** 分组是否被门控开关锁定（如「图片渲染」由 image.mode 门控，关闭时锁定） */
const active_group_locked = computed(
  () => Boolean(active_group_data.value.gated_by) && !gate_value.value,
)

/** 门控开关的显示名，用于锁定遮罩提示 */
const active_group_gate_label = computed(() => {
  const gate_key = active_group_data.value.gated_by
  if (!gate_key) return ''
  return schema.value?.properties?.[gate_key]?.title || gate_key
})

/** 表单草稿同步（字段级，避免整表重建） */
function handle_update(key, value) {
  config_store.update_field(key, value)
}

/** 撤销改动：清空 store 草稿并重建表单内部草稿 */
async function revert_changes() {
  config_store.reset_draft()
  await nextTick()
  form_ref.value?.reset_draft()
}

/** diff 确认后提交：图片模式新开启时先引导依赖，再按需询问重启 */
async function confirm_save() {
  try {
    const changed_keys_list = changes.value.map((change) => change.key)
    const image_mode_turned_on = changes.value.some(
      (change) => change.key === 'image.mode' && change.new_value === true,
    )
    await config_store.save_changes()
    toast.success(t('config_view.toast_saved_hot_reload'))
    diff_open.value = false
    if (image_mode_turned_on) {
      const prompted = await image_deps_ref.value?.prompt()
      if (prompted) return // 依赖下载流程内部处理重启提示
    }
    if (changed_keys_list.some((key) => RESTART_DEPENDENT_KEYS.includes(key))) {
      ask_restart(t('config_view.restart_image_ai'))
    }
  } catch (error) {
    toast.error(error.message || t('config_view.save_failed'))
  }
}
</script>

<template>
  <div>
    <ConfigTabActions
      :change-count="has_changes ? changes.length : 0"
      :saving="saving"
      @revert="revert_changes"
      @save="diff_open = true"
    >
      <template #left>
        <Button variant="secondary" @click="emit('edit-source')">
          <Icon icon="lucide:file-code" width="15" />
          {{ t('config_view.edit_source') }}
        </Button>
      </template>
    </ConfigTabActions>

    <div v-if="loading && !draft" class="card">
      <div class="loading-block">
        <Spinner :size="18" /> {{ t('config_view.tab_basic_loading') }}
      </div>
    </div>

    <div v-else class="config-layout">
      <ConfigGroupNav
        :items="groups"
        :active-id="active_group"
        :changed-keys="changed_keys"
        @select="(id) => (active_group = id)"
      />

      <section class="card config-panel">
        <div class="card-header">
          <h3 class="card-title">{{ active_group_name }}</h3>
        </div>
        <div class="field-list">
          <SchemaForm
            ref="form_ref"
            :schema="schema"
            :fields="active_group_data.keys"
            :values="config_data"
            :nested="true"
            :show-actions="false"
            :keep-draft-on-schema-change="true"
            :locked-keys="active_group_locked ? [active_group_data.gated_by] : []"
            @update="({ key, value }) => handle_update(key, value)"
          />
          <div v-if="active_group_locked" class="field-lock-overlay" role="presentation">
            <Icon icon="lucide:lock" width="18" />
            <p class="field-lock-text">
              {{ t('config_view.tab_basic_lock_hint', { name: active_group_gate_label }) }}
            </p>
          </div>
        </div>
      </section>
    </div>

    <!-- 保存前 diff 预览 -->
    <DiffPreviewDialog
      :open="diff_open"
      :title="t('config_view.diff_toml_title')"
      :description="t('config_view.diff_toml_desc', { count: changes.length })"
      :changes="changes"
      :loading="saving"
      @update:open="(value) => (diff_open = value)"
      @confirm="confirm_save"
    />

    <!-- 图片模式依赖扩展自动下载引导 -->
    <ConfigImageDepsDialog ref="image_deps_ref" />
  </div>
</template>

<style scoped>
.config-layout {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: var(--space-5);
  align-items: start;
}

/* 字段列表容器（字段行样式由 SchemaForm 提供） */
.field-list {
  padding: var(--space-2) var(--space-4);
  position: relative;
}

/* 门控锁定遮罩：门控开关关闭时盖住不可编辑的字段 */
.field-lock-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--text-muted);
  background: color-mix(in srgb, var(--surface) 82%, transparent);
  backdrop-filter: blur(2px);
  border-radius: var(--radius);
  text-align: center;
}

.field-lock-text {
  font-size: var(--text-sm);
  font-weight: 500;
}

@media (max-width: 900px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
}
</style>
