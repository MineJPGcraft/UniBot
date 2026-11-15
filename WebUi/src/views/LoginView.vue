<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { current_locale, set_locale, LOCALES } from '@/i18n'

const router = useRouter()
const { t } = useI18n()
const auth_store = useAuthStore()
const toast = use_toast()
const { run } = use_async_action()

// null 探测中 | 'login' | 'setup'
const mode = ref(null)
const submitting = ref(false)

const login_form = ref({ username: '', password: '' })
const setup_form = ref({
  username: '',
  password: '',
  confirm_password: '',
  nickname: t('login.login_default_nickname'),
})

function next_locale() {
  const index = LOCALES.findIndex((item) => item.value === current_locale())
  return LOCALES[(index + 1) % LOCALES.length].value
}

function toggle_locale() {
  set_locale(next_locale())
}

onMounted(async () => {
  // 已有有效 token 则直接进入
  if (auth_store.is_logged_in) {
    try {
      await auth_store.fetch_me()
      router.replace('/')
      return
    } catch {
      // token 失效，继续走登录流程
    }
  }
  // 探测后端是否已存在账户：已初始化只允许登录，否则自动进入初始化向导
  try {
    const initialized = await auth_store.fetch_auth_status()
    mode.value = initialized ? 'login' : 'setup'
  } catch {
    // 探测失败时保守处理，仅展示登录表单
    mode.value = 'login'
  }
})

async function handle_login() {
  if (!login_form.value.username || !login_form.value.password) {
    toast.error(t('login.login_error_required'))
    return
  }
  const ok = await run(
    () => auth_store.login(login_form.value.username, login_form.value.password),
    t('login.login_failed'),
    submitting,
  )
  if (ok) {
    toast.success(t('login.login_success'))
    router.push('/')
  }
}

async function handle_setup() {
  const { username, password, confirm_password, nickname } = setup_form.value
  if (!username || !password) {
    toast.error(t('login.login_setup_error_required'))
    return
  }
  if (password.length < 6) {
    toast.error(t('login.login_setup_error_password_short'))
    return
  }
  if (password !== confirm_password) {
    toast.error(t('login.login_setup_error_password_mismatch'))
    return
  }
  const ok = await run(
    () => auth_store.setup(username, password, nickname || t('login.login_default_nickname')),
    t('login.login_setup_failed'),
    submitting,
  )
  // 无论成败都回到登录表单：失败时后端可能检测到已有账户（如并发创建）
  mode.value = 'login'
  if (ok) {
    toast.success(t('login.login_setup_success'))
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-panel">
      <div class="locale-toggle">
        <Tooltip :text="t('nav.switch_language')">
          <button class="locale-button" type="button" @click="toggle_locale">
            <Icon icon="lucide:languages" width="16" />
          </button>
        </Tooltip>
      </div>

      <div class="login-brand">
        <div class="login-logo">
          <Icon icon="lucide:bot" width="26" />
        </div>
        <h1 class="login-title">UniBot</h1>
        <p class="login-subtitle">{{ t('login.login_subtitle') }}</p>
      </div>

      <!-- 探测中 -->
      <div v-if="mode === null" class="loading-block">
        <Spinner :size="16" />
        {{ t('login.login_connecting') }}
      </div>

      <!-- 登录 -->
      <form v-else-if="mode === 'login'" class="login-form" @submit.prevent="handle_login">
        <div class="form-row">
          <label class="form-label" for="login-username">{{
            t('login.login_username_label')
          }}</label>
          <Input
            id="login-username"
            v-model="login_form.username"
            :placeholder="t('login.login_username_placeholder')"
            autocomplete="username"
          />
        </div>
        <div class="form-row">
          <label class="form-label" for="login-password">{{
            t('login.login_password_label')
          }}</label>
          <Input
            id="login-password"
            v-model="login_form.password"
            type="password"
            :placeholder="t('login.login_password_placeholder')"
            autocomplete="current-password"
          />
        </div>
        <Button variant="primary" type="submit" :loading="submitting" class="login-submit">
          {{ t('login.login_submit') }}
        </Button>
      </form>

      <!-- 首次初始化 -->
      <form v-else class="login-form" @submit.prevent="handle_setup">
        <div class="setup-notice">
          <Icon icon="lucide:sparkles" width="15" />
          {{ t('login.login_setup_notice') }}
        </div>
        <div class="form-row">
          <label class="form-label" for="setup-username">{{
            t('login.login_username_label')
          }}</label>
          <Input
            id="setup-username"
            v-model="setup_form.username"
            :placeholder="t('login.login_username_example')"
          />
        </div>
        <div class="form-row">
          <label class="form-label" for="setup-nickname">{{
            t('login.login_nickname_label')
          }}</label>
          <Input
            id="setup-nickname"
            v-model="setup_form.nickname"
            :placeholder="t('login.login_nickname_placeholder')"
          />
        </div>
        <div class="form-row">
          <label class="form-label" for="setup-password">{{
            t('login.login_password_label')
          }}</label>
          <Input
            id="setup-password"
            v-model="setup_form.password"
            type="password"
            :placeholder="t('login.login_password_min_placeholder')"
          />
        </div>
        <div class="form-row">
          <label class="form-label" for="setup-confirm">{{
            t('login.login_confirm_password_label')
          }}</label>
          <Input
            id="setup-confirm"
            v-model="setup_form.confirm_password"
            type="password"
            :placeholder="t('login.login_confirm_password_placeholder')"
          />
        </div>
        <Button variant="primary" type="submit" :loading="submitting" class="login-submit">
          {{ t('login.login_create_admin') }}
        </Button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-4);
  background:
    radial-gradient(circle at 20% 20%, var(--accent-soft) 0%, transparent 45%),
    radial-gradient(circle at 85% 80%, var(--success-soft) 0%, transparent 40%), var(--bg);
}

.login-panel {
  position: relative;
  width: min(400px, 100%);
  padding: var(--space-8) var(--space-6);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.locale-toggle {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
}

.locale-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: var(--radius);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background-color var(--transition);
}

.locale-button:hover {
  background: color-mix(in srgb, var(--text) 4%, transparent);
  color: var(--text);
}

.login-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: var(--space-6);
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  background: var(--accent);
  color: #ffffff;
  margin-bottom: var(--space-3);
}

.login-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.login-subtitle {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.login-submit {
  margin-top: var(--space-2);
  height: 38px;
}

.setup-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: var(--radius);
  font-size: var(--text-sm);
}
</style>
