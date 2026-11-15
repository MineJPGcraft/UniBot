<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { use_websocket } from '@/composables/use_websocket'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import TaskCenterDrawer from './TaskCenterDrawer.vue'
import { current_locale, set_locale, LOCALES } from '@/i18n'
import { role_label } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const auth_store = useAuthStore()
const { user } = storeToRefs(auth_store)
const theme_store = useThemeStore()
const { is_dark } = storeToRefs(theme_store)
const { connection_state } = use_websocket()

const breadcrumb = computed(() => t(route.meta.title_key || 'nav.dashboard'))

const ws_dot_class = computed(() => {
  if (connection_state.value === 'connected') return 'ws-dot--connected'
  if (connection_state.value === 'connecting') return 'ws-dot--connecting'
  return 'ws-dot--disconnected'
})

const ws_text = computed(() => {
  if (connection_state.value === 'connected') return t('nav.ws_connected')
  if (connection_state.value === 'connecting') return t('nav.ws_connecting')
  return t('nav.ws_disconnected')
})

const user_menu_items = computed(() => [
  { label: t('nav.user_settings'), icon: 'lucide:user', on_select: () => router.push('/settings') },
  { separator: true },
  {
    label: t('nav.logout'),
    icon: 'lucide:log-out',
    danger: true,
    on_select: async () => {
      await auth_store.logout()
      router.push('/login')
    },
  },
])

const avatar_text = computed(() =>
  (user.value?.nickname || user.value?.username || '?').slice(0, 1),
)

function next_locale() {
  const index = LOCALES.findIndex((item) => item.value === current_locale())
  return LOCALES[(index + 1) % LOCALES.length].value
}

function toggle_locale() {
  set_locale(next_locale())
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <h2 class="topbar-title">{{ breadcrumb }}</h2>
    </div>

    <div class="topbar-right">
      <Tooltip :text="ws_text">
        <span class="ws-indicator">
          <span class="ws-dot" :class="ws_dot_class" />
        </span>
      </Tooltip>

      <TaskCenterDrawer />

      <Tooltip :text="t('nav.switch_language')">
        <button class="locale-toggle" @click="toggle_locale">
          <Icon icon="lucide:languages" width="16" />
        </button>
      </Tooltip>

      <Tooltip :text="t('nav.toggle_theme')">
        <button class="theme-toggle" @click="theme_store.toggle_theme()">
          <Icon :icon="is_dark ? 'lucide:sun' : 'lucide:moon'" width="16" />
        </button>
      </Tooltip>

      <DropdownMenu :items="user_menu_items">
        <template #trigger>
          <button class="user-trigger">
            <span class="user-avatar">{{ avatar_text }}</span>
            <span class="user-name">{{ user?.nickname || user?.username }}</span>
            <Icon icon="lucide:chevron-down" width="14" class="text-muted" />
          </button>
        </template>
        <template #label>
          <div class="menu-user-info">
            <div class="menu-user-name">{{ user?.nickname || user?.username }}</div>
            <div class="menu-user-role">{{ role_label(user?.role) }}</div>
          </div>
        </template>
      </DropdownMenu>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--topbar-height);
  padding: 0 var(--space-6);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.topbar-title {
  font-size: var(--text-md);
  font-weight: 600;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.ws-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  cursor: default;
}

.locale-toggle,
.theme-toggle {
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

.locale-toggle:hover,
.theme-toggle:hover {
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text);
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.ws-dot--connected {
  background: var(--success);
  box-shadow: 0 0 0 3px var(--success-soft);
}

.ws-dot--connecting {
  background: var(--warning);
}

.ws-dot--disconnected {
  background: var(--danger);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius);
  transition: background-color var(--transition);
}

.user-trigger:hover {
  background: color-mix(in srgb, var(--text) 5%, transparent);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
}

.user-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.menu-user-info {
  display: flex;
  flex-direction: column;
}

.menu-user-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.menu-user-role {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
