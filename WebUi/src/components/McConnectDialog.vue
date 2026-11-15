<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/config'
import { use_async_action } from '@/composables/use_async_action'
import Dialog from '@/components/ui/Dialog.vue'
import Tabs from '@/components/ui/Tabs.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'

// 异步组件：CodePanel 静态链会拖入整条 CodeMirror（约 125 kB gzip），
// 而它只在用户点开本弹窗并切到对应页签时才会显示，改为按需加载，
// 避免首页路由把编辑器链路一起下载。
const CodePanel = defineAsyncComponent(() => import('@/components/ui/CodePanel.vue'))

const open = defineModel({ type: Boolean, default: false })

const { t } = useI18n()
const config_store = useConfigStore()
const { env_values } = storeToRefs(config_store)
const { run, busy } = use_async_action()

/** 服务器名称，两端配置中的 server_name 必须一致 */
const server_name = ref('survival')

/** 鉴权令牌，两端保持一致；留空则不校验 */
const access_token = ref('')

/** Bot → MC 模式下 MC 服务器端 WebSocket 地址 */
const mc_ws_url = ref('')

/** 当前连接方式：mc_to_bot = MC 服务器主动连接核心；bot_to_mc = 核心主动连接 MC 服务器 */
const active_tab = ref('mc_to_bot')

/** 核心配置是否已写入 */
const write_done = ref(false)

/** 配置中展示的服务器名称，未填写时用占位符提醒 */
const display_name = computed(
  () => server_name.value.trim() || t('servers.mc_connect_name_fallback'),
)

/** 配置中展示的鉴权令牌 */
const display_token = computed(() => access_token.value.trim())

/** MC 服务器地址是否有效（仅 Bot → MC 模式需要） */
const mc_ws_url_valid = computed(() => /^wss?:\/\//.test(mc_ws_url.value.trim()))

/**
 * 核心侧 WebSocket 地址
 * WebUI 与机器人核心同端口部署，直接取当前访问地址生成，路径固定 /minecraft/ws
 */
const core_ws_url = computed(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/minecraft/ws`
})

/** 写入核心配置的键值（MC → Bot 只写令牌；Bot → MC 额外合并写入 WS 地址表） */
function core_env_fields() {
  const fields = { MINECRAFT_ACCESS_TOKEN: display_token.value }
  if (active_tab.value !== 'bot_to_mc') return fields

  const existing = env_values.value?.MINECRAFT_WS_URLS
  const merged =
    existing && typeof existing === 'object' && !Array.isArray(existing) ? { ...existing } : {}
  merged[display_name.value] = [mc_ws_url.value.trim()]
  fields.MINECRAFT_WS_URLS = merged
  return fields
}

async function write_core_config() {
  const ok = await run(
    () => config_store.save_env_fields(core_env_fields()),
    t('servers.mc_connect_write_failed'),
    busy,
  )
  if (ok) write_done.value = true
}

/** 输入变化后已写入状态失效 */
watch([server_name, access_token, mc_ws_url, active_tab], () => {
  write_done.value = false
})

/** MC 服务器侧鹊桥配置（可直接复制） */
const server_block = computed(() => ({
  title: t('servers.mc_connect_server_block_title'),
  language: 'yaml',
  code:
    active_tab.value === 'mc_to_bot'
      ? [
          `server_name: "${display_name.value}"`,
          `access_token: "${display_token.value}"`,
          '',
          t('servers.mc_connect_code_comment_reverse'),
          'websocket_client:',
          '  enable: true',
          '  reconnect_interval: 5',
          '  reconnect_max_times: 5',
          '  url_list:',
          `    - "${core_ws_url.value}"`,
          '',
          'websocket_server:',
          '  enable: false',
        ].join('\n')
      : [
          `server_name: "${display_name.value}"`,
          `access_token: "${display_token.value}"`,
          '',
          t('servers.mc_connect_code_comment_forward'),
          'websocket_server:',
          '  enable: true',
          '  host: "0.0.0.0"',
          '  port: 8080',
          '',
          'websocket_client:',
          '  enable: false',
        ].join('\n'),
}))
</script>

<template>
  <Dialog
    v-model="open"
    :title="t('servers.mc_connect_dialog_title')"
    :description="t('servers.mc_connect_dialog_description')"
    :hide-footer="true"
    width="min(640px, calc(100vw - 32px))"
  >
    <div class="connect-guide">
      <!-- 基础信息 -->
      <div class="basic-fields">
        <div class="field">
          <label class="field-label" for="mc-connect-server-name">{{
            t('servers.mc_connect_server_name_label')
          }}</label>
          <Input
            id="mc-connect-server-name"
            v-model="server_name"
            :placeholder="t('servers.mc_connect_server_name_placeholder')"
          />
        </div>
        <div class="field">
          <label class="field-label" for="mc-connect-access-token">{{
            t('servers.mc_connect_token_label')
          }}</label>
          <Input
            id="mc-connect-access-token"
            v-model="access_token"
            :placeholder="t('servers.mc_connect_token_placeholder')"
          />
        </div>
        <div v-if="active_tab === 'bot_to_mc'" class="field field--full">
          <label class="field-label" for="mc-connect-server-url">{{
            t('servers.mc_connect_url_label')
          }}</label>
          <Input
            id="mc-connect-server-url"
            v-model="mc_ws_url"
            :placeholder="t('servers.mc_connect_url_placeholder')"
          />
        </div>
      </div>

      <!-- 连接方式 -->
      <Tabs
        v-model="active_tab"
        :tabs="[
          { value: 'mc_to_bot', label: 'MC → Bot' },
          { value: 'bot_to_mc', label: 'Bot → MC' },
        ]"
      >
        <template #[active_tab]>
          <p v-if="active_tab === 'mc_to_bot'" class="mode-note mode-note--recommend">
            <Icon icon="lucide:thumbs-up" width="13" />
            {{ t('servers.mc_connect_mode_recommend_note') }}
          </p>
          <p v-else class="mode-note">
            <Icon icon="lucide:info" width="13" />
            {{ t('servers.mc_connect_mode_forward_note') }}
          </p>

          <!-- 核心侧：一键写入 -->
          <div class="core-card">
            <div class="core-card-head">
              <span class="core-card-title">
                <Icon icon="lucide:server" width="14" />
                {{ t('servers.mc_connect_core_side_title') }}
              </span>
              <span v-if="write_done" class="core-card-done">
                <Icon icon="lucide:circle-check" width="14" />
                {{ t('servers.mc_connect_written_hint') }}
              </span>
            </div>
            <p class="core-card-desc">
              {{
                active_tab === 'mc_to_bot'
                  ? t('servers.mc_connect_core_desc_reverse')
                  : t('servers.mc_connect_core_desc_forward')
              }}
            </p>
            <Button
              size="sm"
              :variant="write_done ? 'secondary' : 'primary'"
              :disabled="active_tab === 'bot_to_mc' && !mc_ws_url_valid"
              :loading="busy"
              @click="write_core_config"
            >
              <Icon :icon="write_done ? 'lucide:check' : 'lucide:pen-line'" width="14" />
              {{
                write_done ? t('servers.mc_connect_written') : t('servers.mc_connect_write_action')
              }}
            </Button>
          </div>

          <!-- MC 侧：复制配置 -->
          <CodePanel
            class="mode-panel"
            :title="server_block.title"
            :language="server_block.language"
            :code="server_block.code"
          />
        </template>
      </Tabs>

      <p class="config-tip">
        {{ t('servers.mc_connect_tip_plugin_config') }}
        <code class="mono">./plugins/QueQiao/config.yml</code
        >{{ t('servers.mc_connect_tip_mod_config') }}
        <code class="mono">./config/QueQiao/config.yml</code
        >{{ t('servers.mc_connect_tip_both_prefix') }}
        <code class="mono">server_name</code>
        {{ t('servers.mc_connect_tip_must_match') }}
      </p>

      <!-- 文档引导 -->
      <a
        class="docs-entry"
        href="https://bot.mcjpg.dev/adapter/usage.html"
        target="_blank"
        rel="noopener"
      >
        <span class="docs-entry-icon">
          <Icon icon="lucide:book-open" width="16" />
        </span>
        <span class="docs-entry-body">
          <span class="docs-entry-title">{{ t('servers.mc_connect_docs_entry_title') }}</span>
          <span class="docs-entry-desc">{{ t('servers.mc_connect_docs_entry_description') }}</span>
        </span>
        <Icon icon="lucide:chevron-right" width="16" class="docs-entry-arrow" />
      </a>
    </div>
  </Dialog>
</template>

<style scoped>
.connect-guide {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.basic-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field--full {
  grid-column: 1 / -1;
}

.field-label {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-secondary);
}

.mode-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  background: var(--surface-sunken);
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.mode-note svg {
  flex-shrink: 0;
}

.mode-note--recommend {
  background: var(--accent-soft);
  color: var(--text-secondary);
}

.mode-note--recommend svg {
  color: var(--accent);
}

/* 核心侧写入卡 */
.core-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.core-card-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.core-card-title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.core-card-done {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--success);
}

.core-card-desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.6;
}

.mode-panel {
  margin-top: var(--space-1);
}

.config-tip {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.7;
}

/* 文档入口 */
.docs-entry {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  transition:
    border-color var(--transition),
    background-color var(--transition);
}

.docs-entry:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.docs-entry-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.docs-entry-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.docs-entry-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.docs-entry-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.docs-entry-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition:
    transform var(--transition),
    color var(--transition);
}

.docs-entry:hover .docs-entry-arrow {
  transform: translateX(2px);
  color: var(--accent);
}
</style>
