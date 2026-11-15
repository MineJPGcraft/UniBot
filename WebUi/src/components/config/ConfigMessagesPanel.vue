<script setup>
/**
 * 配置中心：消息文本面板。
 *
 * 自包含「说明栏 + 消息树 + 撤销/保存」。消息语言跟随面板界面语言：语言切换后
 * 重新拉取分组树（与 config store 的 messages_language 比对，避免重复请求）。
 */
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { current_locale } from '@/i18n'
import { useConfigStore } from '@/stores/config'
import { use_toast } from '@/composables/use_toast'
import Spinner from '@/components/ui/Spinner.vue'
import MessageTree from '@/components/config/MessageTree.vue'
import ConfigTabActions from '@/components/config/ConfigTabActions.vue'

const { t } = useI18n()
const config_store = useConfigStore()
const toast = use_toast()
const {
  messages_language,
  messages_tree,
  messages_draft,
  messages_loading,
  messages_saving,
  messages_changes,
  has_messages_changes,
} = storeToRefs(config_store)

/** 是否已加载过（失败时复位，允许重试） */
const loaded = ref(false)

/** 按需加载分组树（消息语言跟随界面语言，语言变化时重拉） */
async function ensure_loaded() {
  const language = current_locale()
  if (loaded.value && messages_language.value === language) return
  loaded.value = true
  try {
    await config_store.fetch_messages(language)
  } catch (error) {
    loaded.value = false
    toast.error(error.message || t('config_view.toast_load_messages_failed'))
  }
}

// 界面语言切换后重拉：消息树带 language 查询参数，不在 use_locale_refresh 的
// 通用刷新清单内，由本组件自行跟随
watch(() => current_locale(), ensure_loaded)

// Tabs 会卸载非活动面板，切到本页时组件才挂载，挂载即按需加载
onMounted(ensure_loaded)

function handle_update(key, value) {
  config_store.update_message(key, value)
}

function reset() {
  config_store.reset_messages_draft()
}

async function confirm_save() {
  try {
    const count = await config_store.save_messages()
    toast.success(
      count > 0 ? t('config_view.toast_messages_saved') : t('config_view.no_changes_detected'),
    )
  } catch (error) {
    toast.error(error.message || t('config_view.save_failed'))
  }
}
</script>

<template>
  <div>
    <ConfigTabActions
      :change-count="has_messages_changes ? messages_changes.length : 0"
      :saving="messages_saving"
      @revert="reset"
      @save="confirm_save"
    >
      <template #left>
        <span class="text-xs text-muted">
          {{ t('config_view.tab_messages_sub_prefix') }}
          <code class="mono message-code">{{
            t('config_view.tab_messages_placeholder_example')
          }}</code>
          {{ t('config_view.tab_messages_sub_suffix') }}
        </span>
      </template>
    </ConfigTabActions>

    <div v-if="messages_loading" class="card">
      <div class="loading-block">
        <Spinner :size="18" /> {{ t('config_view.tab_messages_loading') }}
      </div>
    </div>

    <MessageTree v-else :tree="messages_tree" :draft="messages_draft" @update="handle_update" />
  </div>
</template>

<style scoped>
/* 消息文本编辑器：占位符示例代码样式 */
.message-code {
  padding: 1px 5px;
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--text) 8%, transparent);
  font-weight: 600;
}
</style>
