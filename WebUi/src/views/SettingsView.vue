<script setup>
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '@/stores/auth'
import { useStatusStore } from '@/stores/status'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Badge from '@/components/ui/Badge.vue'
import { role_label, format_datetime, format_uptime } from '@/utils/format'

const auth_store = useAuthStore()
const status_store = useStatusStore()
const { t } = useI18n()
const toast = use_toast()
const { run } = use_async_action()
const { user } = storeToRefs(auth_store)
const { status } = storeToRefs(status_store)

const nickname = ref('')
// fetch_me 是异步的：用户信息就绪后同步昵称，避免首次直达本页时表单为空
watch(
  user,
  (current) => {
    if (current?.nickname) nickname.value = current.nickname
  },
  { immediate: true },
)
const saving_profile = ref(false)

const password_form = ref({ old_password: '', new_password: '', confirm_password: '' })
const saving_password = ref(false)

const avatar_text = computed(() =>
  (user.value?.nickname || user.value?.username || '?').slice(0, 1),
)

const checking_update = ref(false)
const updating = ref(false)

const update_hint = computed(() => {
  if (!status.value?.latest_version) return null
  if (status.value.has_update) {
    return {
      variant: 'warning',
      text: t('settings.update_available_hint', { version: status.value.latest_version }),
    }
  }
  return { variant: 'success', text: t('settings.up_to_date_hint') }
})

async function check_update() {
  const ok = await run(
    () => status_store.check_update(),
    t('settings.check_failed'),
    checking_update,
  )
  if (!ok) return
  if (status.value?.has_update) {
    toast.info(t('settings.update_available_toast', { version: status.value.latest_version }))
  } else {
    toast.success(t('settings.up_to_date_toast'))
  }
}

async function update_bot() {
  const ok = await run(() => status_store.update_bot(), t('settings.update_failed'), updating)
  if (ok) {
    toast.success(t('settings.update_success'))
  }
}

const about_links = computed(() => [
  {
    label: t('settings.link_website'),
    value: 'bot.mcjpg.dev',
    url: 'https://bot.mcjpg.dev/',
    icon: 'lucide:globe',
  },
  {
    label: t('settings.link_project'),
    value: 'github.com/MineJPGcraft/UniBot',
    url: 'https://github.com/MineJPGcraft/UniBot',
    icon: 'lucide:github',
  },
  {
    label: t('settings.link_qq_group'),
    value: '962802248',
    url: 'https://qm.qq.com/q/qyq2XH6qkw',
    icon: 'lucide:users',
  },
])

async function save_profile() {
  if (!nickname.value.trim()) {
    toast.error(t('settings.nickname_required'))
    return
  }
  const ok = await run(
    () => auth_store.update_profile(nickname.value.trim()),
    t('settings.profile_update_failed'),
    saving_profile,
  )
  if (ok) {
    toast.success(t('settings.nickname_updated'))
  }
}

async function save_password() {
  const { old_password, new_password, confirm_password } = password_form.value
  if (!old_password || !new_password) {
    toast.error(t('settings.password_form_incomplete'))
    return
  }
  if (new_password.length < 6) {
    toast.error(t('settings.password_too_short'))
    return
  }
  if (new_password !== confirm_password) {
    toast.error(t('settings.password_mismatch'))
    return
  }
  const ok = await run(
    () => auth_store.change_password(old_password, new_password),
    t('settings.password_change_failed'),
    saving_password,
  )
  if (ok) {
    toast.success(t('settings.password_changed'))
    password_form.value = { old_password: '', new_password: '', confirm_password: '' }
  }
}
</script>

<template>
  <div class="page settings-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('settings.page_title') }}</h1>
        <p class="page-desc">{{ t('settings.page_description') }}</p>
      </div>
    </div>

    <!-- 账户信息 -->
    <section class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('settings.account_section') }}</h3>
      </div>
      <div class="card-body profile-body">
        <div class="profile-card">
          <span class="profile-avatar">{{ avatar_text }}</span>
          <div class="profile-text">
            <div class="profile-name">
              {{ user?.nickname || user?.username }}
              <Badge variant="accent">{{ role_label(user?.role) }}</Badge>
            </div>
            <div class="profile-meta mono">@{{ user?.username }}</div>
            <div class="profile-meta text-muted">
              {{ t('settings.registered_at', { time: format_datetime(user?.created_at) }) }}
            </div>
          </div>
        </div>

        <form class="profile-form" @submit.prevent="save_profile">
          <div class="form-row">
            <label class="form-label">{{ t('settings.nickname_label') }}</label>
            <Input v-model="nickname" :placeholder="t('settings.nickname_placeholder')" />
          </div>
          <Button variant="primary" type="submit" :loading="saving_profile">{{
            t('settings.save_nickname')
          }}</Button>
        </form>
      </div>
    </section>

    <!-- 修改密码 -->
    <section class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('settings.password_section') }}</h3>
      </div>
      <div class="card-body">
        <form class="password-form" @submit.prevent="save_password">
          <div class="form-row">
            <label class="form-label">{{ t('settings.current_password_label') }}</label>
            <Input v-model="password_form.old_password" type="password" />
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('settings.new_password_label') }}</label>
            <Input
              v-model="password_form.new_password"
              type="password"
              :placeholder="t('settings.new_password_placeholder')"
            />
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('settings.confirm_password_label') }}</label>
            <Input v-model="password_form.confirm_password" type="password" />
          </div>
          <Button variant="primary" type="submit" :loading="saving_password">
            <Icon icon="lucide:key-round" width="14" />
            {{ t('settings.change_password') }}
          </Button>
        </form>
      </div>
    </section>

    <!-- 当前会话 -->
    <section class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('settings.session_section') }}</h3>
      </div>
      <div class="card-body session-body">
        <div class="session-row">
          <span class="session-label">{{ t('settings.last_login_label') }}</span>
          <span>{{ format_datetime(user?.last_login_at) }}</span>
        </div>
        <div class="session-row">
          <span class="session-label">{{ t('settings.token_lifetime_label') }}</span>
          <span>{{ t('settings.token_lifetime_value') }}</span>
        </div>
      </div>
    </section>

    <!-- 关于 -->
    <section class="card about-card">
      <div class="about-banner">
        <div class="about-banner-grid" aria-hidden="true"></div>
        <div class="about-identity">
          <span class="about-logo"><Icon icon="lucide:bot" width="22" /></span>
          <div class="about-title-block">
            <div class="about-name">
              UniBot
              <Badge variant="accent">{{ status?.version || '—' }}</Badge>
            </div>
            <p class="about-desc">{{ t('settings.about_description') }}</p>
          </div>
        </div>
        <div class="about-banner-side">
          <span class="about-pulse">
            <span class="pulse-dot" />
            {{ t('settings.running_duration', { duration: format_uptime(status?.uptime) }) }}
          </span>
          <div class="about-banner-actions">
            <button
              v-if="auth_store.is_admin && status?.has_update"
              class="update-button"
              type="button"
              :disabled="updating"
              @click="update_bot"
            >
              <Icon icon="lucide:download" width="13" :class="{ spinning: updating }" />
              {{ t('settings.update_now') }}
            </button>
            <button
              v-if="auth_store.is_admin"
              class="check-update-button"
              type="button"
              :disabled="checking_update"
              @click="check_update"
            >
              <Icon icon="lucide:refresh-cw" width="13" :class="{ spinning: checking_update }" />
              {{ t('settings.check_update') }}
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="update_hint"
        class="about-update-bar"
        :class="`about-update-bar--${update_hint.variant}`"
      >
        <Icon
          :icon="
            update_hint.variant === 'warning' ? 'lucide:arrow-up-circle' : 'lucide:check-circle-2'
          "
          width="15"
        />
        <span>{{ update_hint.text }}</span>
        <a
          v-if="update_hint.variant === 'warning'"
          class="about-update-link"
          href="https://github.com/MineJPGcraft/UniBot/releases/latest"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ t('settings.download_link') }}
          <Icon icon="lucide:arrow-up-right" width="13" />
        </a>
      </div>

      <div class="card-body about-body">
        <a
          v-for="link in about_links"
          :key="link.label"
          class="about-link"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="about-link-icon"><Icon :icon="link.icon" width="15" /></span>
          <span class="about-link-label">{{ link.label }}</span>
          <span class="about-link-value mono">{{ link.value }}</span>
          <Icon class="about-link-arrow" icon="lucide:arrow-up-right" width="14" />
        </a>
      </div>
    </section>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 760px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.settings-page .page-header {
  margin-bottom: 0;
}

.profile-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  align-items: center;
}

.profile-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.profile-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
  font-size: var(--text-xl);
  font-weight: 700;
  text-transform: uppercase;
  flex-shrink: 0;
}

.profile-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.profile-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-md);
  font-weight: 600;
}

.profile-meta {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-items: flex-start;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 360px;
}

.password-form .ui-button,
.password-form button {
  align-self: flex-start;
}

.session-body {
  display: flex;
  flex-direction: column;
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border);
  font-size: var(--text-sm);
}

.session-row:last-child {
  border-bottom: none;
}

.session-label {
  color: var(--text-muted);
}

/* 关于卡片 */
.about-card {
  overflow: hidden;
}

.about-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5);
  border-bottom: 1px solid var(--border);
  background: linear-gradient(160deg, var(--surface) 0%, var(--accent-soft) 100%);
  overflow: hidden;
}

.about-banner-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: linear-gradient(105deg, transparent 25%, #000 100%);
  pointer-events: none;
}

.about-identity {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.about-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--accent);
  color: #ffffff;
  box-shadow: var(--shadow-md);
  flex-shrink: 0;
}

.about-title-block {
  display: flex;
  flex-direction: column;
}

.about-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.about-desc {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.about-pulse {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.about-banner-side {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-2);
}

.about-banner-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.check-update-button,
.update-button {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.check-update-button:hover:not(:disabled),
.update-button:hover:not(:disabled) {
  background: var(--accent-soft);
  color: var(--accent);
}

.check-update-button:focus-visible,
.update-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.check-update-button:disabled,
.update-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.update-button {
  border-color: var(--accent);
  background: var(--accent);
  color: #ffffff;
}

.update-button:hover:not(:disabled) {
  background: var(--accent-strong);
  color: #ffffff;
}

.about-update-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border);
  font-size: var(--text-sm);
}

.about-update-bar--warning {
  background: var(--warning-soft);
  color: var(--warning);
}

.about-update-bar--success {
  background: var(--success-soft);
  color: var(--success);
}

.about-update-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  color: inherit;
  font-weight: 500;
}

.about-update-link:hover {
  text-decoration: underline;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success);
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--success) 45%, transparent);
  }

  70% {
    box-shadow: 0 0 0 6px transparent;
  }

  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

.about-body {
  display: flex;
  flex-direction: column;
  padding: var(--space-2) var(--space-3);
}

.about-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  color: var(--text);
  text-decoration: none;
  transition: background-color var(--transition);
}

a.about-link:hover {
  background: var(--hover);
}

.about-link-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  flex-shrink: 0;
}

.about-link-label {
  width: 88px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.about-link-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.about-link-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color var(--transition);
}

a.about-link:hover .about-link-arrow {
  color: var(--accent);
}

@media (max-width: 700px) {
  .profile-body {
    grid-template-columns: 1fr;
  }

  .about-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .about-banner-side {
    align-items: flex-start;
  }
}
</style>
