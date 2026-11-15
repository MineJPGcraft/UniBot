<script setup>
/**
 * 配置中心：.env 面板。
 *
 * 自包含「分组导航 + 表单 + 撤销/保存 + 保存前 diff 预览」。.env 改动一律需要重启
 * 才生效，保存成功后询问重启。当前分组经 `v-model` 由父级持有，便于同步 URL query
 * 与深链定位。
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

const emit = defineEmits(['edit-source'])

/** 当前选中的环境变量分组 id */
const active_group = defineModel({ type: String, default: '' })

const { t } = useI18n()
const config_store = useConfigStore()
const toast = use_toast()
const { ask_restart } = use_restart()
const {
  env_schema,
  env_groups,
  env_values,
  env_loading,
  env_saving,
  env_changes,
  has_env_changes,
} = storeToRefs(config_store)

const diff_open = ref(false)
const form_ref = ref(null)

/** 分组就绪后默认选中第一个（父级深链传入的非空值不覆盖） */
watch(
  env_groups,
  (value) => {
    if (!active_group.value && value.length > 0) active_group.value = value[0].id
  },
  { immediate: true },
)

/** 当前分组对象（含 keys 等元信息） */
const active_group_data = computed(
  () =>
    env_groups.value.find(
      (group) => group.id === active_group.value || group.name === active_group.value,
    ) || { keys: [] },
)

/** 当前分组显示名 */
const active_group_name = computed(() => active_group_data.value.name || active_group.value)

/** 已变更字段 key 集合（Set 查找，避免模板里嵌套 some 的 O(n²) 比较） */
const changed_keys = computed(() => new Set(env_changes.value.map((change) => change.key)))

/** 表单草稿同步（字段级，避免整表重建） */
function handle_update(key, value) {
  config_store.update_env_field(key, value)
}

/** 撤销改动：清空 store 草稿并重建表单内部草稿 */
async function revert_changes() {
  config_store.reset_env_draft()
  await nextTick()
  form_ref.value?.reset_draft()
}

/** diff 确认后提交，.env 改动需重启生效 */
async function confirm_save() {
  try {
    await config_store.save_env_changes()
    toast.success(t('config_view.toast_env_saved_needs_restart'))
    diff_open.value = false
    ask_restart(t('config_view.restart_env_changed'))
  } catch (error) {
    toast.error(error.message || t('config_view.save_failed'))
  }
}
</script>

<template>
  <div>
    <ConfigTabActions
      :change-count="has_env_changes ? env_changes.length : 0"
      :saving="env_saving"
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

    <div v-if="env_loading" class="card">
      <div class="loading-block"><Spinner :size="18" /> {{ t('config_view.tab_env_loading') }}</div>
    </div>

    <div v-else class="config-layout">
      <ConfigGroupNav
        :items="env_groups"
        :active-id="active_group"
        :changed-keys="changed_keys"
        @select="(id) => (active_group = id)"
      />

      <section class="card config-panel">
        <div class="card-header">
          <h3 class="card-title">{{ active_group_name }}</h3>
          <span class="text-xs text-muted">{{ t('config_view.tab_env_restart_hint') }}</span>
        </div>
        <div class="field-list">
          <SchemaForm
            ref="form_ref"
            :schema="env_schema"
            :fields="active_group_data.keys"
            :values="env_values"
            :show-actions="false"
            :keep-draft-on-schema-change="true"
            @update="({ key, value }) => handle_update(key, value)"
          />
        </div>
      </section>
    </div>

    <!-- 保存前 diff 预览 -->
    <DiffPreviewDialog
      :open="diff_open"
      :title="t('config_view.diff_env_title')"
      :description="t('config_view.diff_env_desc', { count: env_changes.length })"
      :changes="env_changes"
      :loading="env_saving"
      @update:open="(value) => (diff_open = value)"
      @confirm="confirm_save"
    />
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
}

@media (max-width: 900px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
}
</style>
