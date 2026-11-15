<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '@/stores/auth'
import { use_restart } from '@/composables/use_restart'

const { t } = useI18n()
const auth_store = useAuthStore()
const { restarting, ask_restart } = use_restart()

const nav_items = [
  { path: '/', label_key: 'nav.dashboard', icon: 'lucide:layout-dashboard', admin_only: false },
  {
    path: '/servers',
    label_key: 'layout.sidebar_nav_servers',
    icon: 'lucide:server',
    admin_only: false,
  },
  {
    path: '/statistics',
    label_key: 'layout.sidebar_nav_statistics',
    icon: 'lucide:chart-column',
    admin_only: false,
  },
  {
    path: '/players',
    label_key: 'layout.sidebar_nav_players',
    icon: 'lucide:users',
    admin_only: false,
  },
  {
    path: '/config',
    label_key: 'layout.sidebar_nav_config',
    icon: 'lucide:settings-2',
    admin_only: true,
  },
  {
    path: '/logs',
    label_key: 'layout.sidebar_nav_logs',
    icon: 'lucide:scroll-text',
    admin_only: false,
  },
  {
    path: '/plugins',
    label_key: 'layout.sidebar_nav_plugins',
    icon: 'lucide:puzzle',
    admin_only: false,
  },
  {
    path: '/extensions',
    label_key: 'layout.sidebar_nav_extensions',
    icon: 'lucide:package',
    admin_only: false,
  },
  {
    path: '/adapters',
    label_key: 'layout.sidebar_nav_adapters',
    icon: 'lucide:unplug',
    admin_only: false,
  },
  {
    path: '/users',
    label_key: 'layout.sidebar_nav_users',
    icon: 'lucide:shield-check',
    admin_only: true,
  },
]
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-logo">
        <Icon icon="lucide:bot" width="20" />
      </div>
      <div class="brand-text">
        <span class="brand-name">UniBot</span>
        <span class="brand-sub">{{ t('layout.sidebar_brand_sub') }}</span>
      </div>
      <button
        v-if="auth_store.is_admin"
        class="restart-button"
        type="button"
        :title="t('layout.sidebar_restart_title')"
        :aria-label="t('layout.sidebar_restart_title')"
        :disabled="restarting"
        @click="
          ask_restart(
            t('layout.sidebar_restart_message'),
            t('layout.sidebar_restart_confirm_title'),
          )
        "
      >
        <Icon icon="lucide:refresh-cw" width="16" :class="{ spinning: restarting }" />
      </button>
    </div>

    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in nav_items.filter((nav) => !nav.admin_only || auth_store.is_admin)"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'nav-item--exact': item.path === '/' }"
      >
        <Icon :icon="item.icon" width="16" />
        <span>{{ t(item.label_key) }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <RouterLink to="/settings" class="nav-item">
        <Icon icon="lucide:settings" width="16" />
        <span>{{ t('nav.settings') }}</span>
      </RouterLink>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  height: 100%;
  background: var(--surface);
  border-right: 1px solid var(--border);
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
  flex: 1;
}

.brand-name {
  font-size: var(--text-md);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.brand-sub {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.restart-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition:
    background-color var(--transition),
    color var(--transition);
}

.restart-button:hover:not(:disabled) {
  background: var(--danger-soft);
  color: var(--danger);
}

.restart-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.restart-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  overflow-y: auto;
}

.sidebar-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--border);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.nav-item:hover {
  background: color-mix(in srgb, var(--text) 4%, transparent);
  color: var(--text);
}

.nav-item.router-link-active {
  background: var(--accent-soft);
  color: var(--accent);
}

/* 非首页的精确匹配由嵌套路由天然保证，这里仅首页需 exact */
.nav-item--exact.router-link-active:not(.router-link-exact-active) {
  background: transparent;
  color: var(--text-muted);
}
</style>
