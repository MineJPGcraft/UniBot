<script setup>
/**
 * 扩展配置弹窗：复用通用 SchemaForm 动态表单。
 *
 *    与配置中心一致的交互：保存操作位于表单右上角操作栏（含改动计数），
 *    无改动时「取消」与「保存」均不可用；操作栏左侧提供「在配置中心打开」
 *    入口（配置中心为管理员专属路由，非管理员禁用）。
 */
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '@/stores/auth'
import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import SchemaForm from '@/components/ui/SchemaForm.vue'

const props = defineProps({
  extension: { type: Object, default: null },
  schema: { type: Object, default: null },
  values: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['save'])

const { t } = useI18n()
const router = useRouter()
const auth_store = useAuthStore()

const open = defineModel({ type: Boolean, default: false })

/** 跳转到配置中心的扩展配置 Tab，并预选当前扩展（仅管理员可用） */
function open_in_config_page() {
  if (!auth_store.is_admin) return
  open.value = false
  const query = { tab: 'extensions' }
  if (props.extension?.id) query.extension = props.extension.id
  router.push({ name: 'ConfigView', query })
}
</script>

<template>
  <Dialog
    v-model="open"
    :title="
      t('extensions.config_dialog_title', {
        name: extension?.name || t('extensions.config_dialog_default_name'),
      })
    "
    :description="extension?.description || ''"
    hide-footer
    width="70vw"
  >
    <SchemaForm
      :schema="schema"
      :values="values"
      :loading="loading"
      :saving="saving"
      :keep-draft-on-schema-change="true"
      @save="(payload) => emit('save', payload)"
    >
      <template #actions-left>
        <Button
          variant="ghost"
          size="sm"
          class="config-page-link"
          :disabled="!auth_store.is_admin"
          :title="t('extensions.config_dialog_open_config_page')"
          @click="open_in_config_page"
        >
          <Icon icon="lucide:external-link" width="14" />
          {{ t('extensions.config_dialog_open_config_page') }}
        </Button>
      </template>
    </SchemaForm>
  </Dialog>
</template>
