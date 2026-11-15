<script setup>
import { computed, ref, onActivated, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Badge from '@/components/ui/Badge.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import Pagination from '@/components/ui/Pagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { role_label, format_datetime } from '@/utils/format'

const user_store = useUserStore()
const auth_store = useAuthStore()
const { t } = useI18n()
const toast = use_toast()
const { run } = use_async_action()
const { user_list, total, page, page_size, keyword, loading } = storeToRefs(user_store)

const search_text = ref('')
const submitting = ref(false)

const role_options = computed(() => [
  { value: 'admin', label: t('users.role_admin') },
  { value: 'operator', label: t('users.role_operator') },
  { value: 'viewer', label: t('users.role_viewer') },
])

const role_badge_variant = { admin: 'accent', operator: 'success', viewer: 'neutral' }

// 新建用户
const create_open = ref(false)
const create_form = ref({ username: '', password: '', nickname: '', role: 'viewer' })

// 编辑用户
const edit_open = ref(false)
const edit_form = ref({ user_id: '', nickname: '', role: 'viewer' })

// 重置密码
const reset_open = ref(false)
const reset_form = ref({ user_id: '', username: '', password: '' })

// 删除用户
const delete_target = ref(null)
const deleting = ref(false)

onMounted(() => {
  refresh()
})

// 页面被 KeepAlive 缓存：切回时静默刷新用户列表（首次挂载由 onMounted 负责，不重复请求）
let activated_once = false
onActivated(() => {
  if (!activated_once) {
    activated_once = true
    return
  }
  user_store.fetch_users().catch((error) => console.warn('fetch_users failed', error))
})

async function refresh() {
  await run(() => user_store.fetch_users(), t('users.fetch_failed'))
}

function handle_search() {
  user_store.set_keyword(search_text.value.trim())
  refresh()
}

function handle_page_change(target_page) {
  user_store.set_page(target_page)
  refresh()
}

async function submit_create() {
  const { username, password, nickname, role } = create_form.value
  if (!username.trim() || !password.trim()) {
    toast.error(t('users.create_missing_fields'))
    return
  }
  const ok = await run(
    () =>
      user_store.create_user({
        username: username.trim(),
        password,
        nickname: nickname.trim() || username.trim(),
        role,
      }),
    t('users.create_failed'),
    submitting,
  )
  if (ok) {
    toast.success(t('users.create_success'))
    create_form.value = { username: '', password: '', nickname: '', role: 'viewer' }
    create_open.value = false
  }
}

function open_edit(user) {
  edit_form.value = { user_id: user.user_id, nickname: user.nickname, role: user.role }
  edit_open.value = true
}

async function submit_edit() {
  const ok = await run(
    () =>
      user_store.update_user(edit_form.value.user_id, {
        nickname: edit_form.value.nickname,
        role: edit_form.value.role,
      }),
    t('users.update_failed'),
    submitting,
  )
  if (ok) {
    toast.success(t('users.update_success'))
    edit_open.value = false
  }
}

function open_reset(user) {
  reset_form.value = { user_id: user.user_id, username: user.username, password: '' }
  reset_open.value = true
}

async function submit_reset() {
  if (!reset_form.value.password) {
    toast.error(t('users.reset_missing_password'))
    return
  }
  const ok = await run(
    () => user_store.reset_password(reset_form.value.user_id, reset_form.value.password),
    t('users.reset_failed'),
    submitting,
  )
  if (ok) {
    toast.success(t('users.reset_success'))
    reset_open.value = false
  }
}

function confirm_delete(user) {
  delete_target.value = user
}

async function submit_delete() {
  const ok = await run(
    () => user_store.delete_user(delete_target.value.user_id),
    t('users.delete_failed'),
    deleting,
  )
  if (ok) {
    toast.success(t('users.delete_success'))
    delete_target.value = null
  }
}

function row_menu_items(user) {
  const is_self = user.user_id === auth_store.user?.user_id
  return [
    {
      label: t('users.menu_edit_profile'),
      icon: 'lucide:pencil',
      on_select: () => open_edit(user),
    },
    {
      label: t('users.menu_reset_password'),
      icon: 'lucide:key-round',
      on_select: () => open_reset(user),
    },
    { separator: true },
    {
      label: t('users.menu_delete_user'),
      icon: 'lucide:trash-2',
      danger: true,
      disabled: is_self,
      on_select: () => confirm_delete(user),
    },
  ]
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('users.page_title') }}</h1>
        <p class="page-desc">{{ t('users.page_description') }}</p>
      </div>
      <div class="page-actions">
        <Button variant="primary" @click="create_open = true">
          <Icon icon="lucide:user-plus" width="15" />
          {{ t('users.create_user') }}
        </Button>
      </div>
    </div>

    <section class="card">
      <div class="table-toolbar">
        <form class="search-box" @submit.prevent="handle_search">
          <Icon icon="lucide:search" width="15" class="search-icon" />
          <Input
            v-model="search_text"
            :placeholder="t('users.search_placeholder')"
            @keydown.enter="handle_search"
          />
        </form>
        <Button variant="secondary" icon-only @click="refresh">
          <Icon icon="lucide:refresh-cw" width="15" />
        </Button>
      </div>

      <div v-if="loading && user_list.length === 0" class="loading-block">
        <Spinner :size="18" /> {{ t('common.loading') }}
      </div>

      <EmptyState
        v-else-if="user_list.length === 0"
        icon="lucide:users"
        :title="t('users.empty_title')"
        :description="keyword ? t('users.empty_search_result', { keyword }) : ''"
      />

      <table v-else class="ui-table">
        <thead>
          <tr>
            <th>{{ t('users.column_user') }}</th>
            <th>{{ t('users.column_role') }}</th>
            <th>{{ t('users.column_created_at') }}</th>
            <th>{{ t('users.column_last_login') }}</th>
            <th class="col-actions">{{ t('users.column_actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in user_list" :key="user.user_id">
            <td>
              <div class="user-cell">
                <span class="user-avatar">{{ (user.nickname || user.username).slice(0, 1) }}</span>
                <div class="user-text">
                  <span class="user-nickname">
                    {{ user.nickname || user.username }}
                    <Badge v-if="user.user_id === auth_store.user?.user_id" variant="accent">{{
                      t('users.self_badge')
                    }}</Badge>
                  </span>
                  <span class="user-username mono">@{{ user.username }}</span>
                </div>
              </div>
            </td>
            <td>
              <Badge :variant="role_badge_variant[user.role]">{{ role_label(user.role) }}</Badge>
            </td>
            <td class="text-muted">{{ format_datetime(user.created_at) }}</td>
            <td class="text-muted">{{ format_datetime(user.last_login_at) }}</td>
            <td class="col-actions">
              <DropdownMenu :items="row_menu_items(user)">
                <template #trigger>
                  <Button variant="ghost" size="sm" icon-only>
                    <Icon icon="lucide:more-horizontal" width="16" />
                  </Button>
                </template>
              </DropdownMenu>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="total > 0" class="table-footer">
        <Pagination
          :page="page"
          :page-size="page_size"
          :total="total"
          @page-change="handle_page_change"
        />
      </div>
    </section>

    <!-- 新建用户 -->
    <Dialog
      v-model="create_open"
      :title="t('users.create_dialog_title')"
      :confirm-text="t('users.create_confirm')"
      :loading="submitting"
      @confirm="submit_create"
    >
      <div class="form-row">
        <label class="form-label">{{ t('users.field_username') }}</label>
        <Input v-model="create_form.username" :placeholder="t('users.username_placeholder')" />
      </div>
      <div class="form-row">
        <label class="form-label">{{ t('users.field_nickname') }}</label>
        <Input v-model="create_form.nickname" :placeholder="t('users.nickname_placeholder')" />
      </div>
      <div class="form-row">
        <label class="form-label">{{ t('users.field_password') }}</label>
        <Input
          v-model="create_form.password"
          type="password"
          :placeholder="t('users.password_placeholder')"
        />
      </div>
      <div class="form-row">
        <label class="form-label">{{ t('users.field_role') }}</label>
        <Select v-model="create_form.role" :options="role_options" />
      </div>
    </Dialog>

    <!-- 编辑用户 -->
    <Dialog
      v-model="edit_open"
      :title="t('users.edit_dialog_title')"
      :confirm-text="t('common.save')"
      :loading="submitting"
      @confirm="submit_edit"
    >
      <div class="form-row">
        <label class="form-label">{{ t('users.field_nickname') }}</label>
        <Input v-model="edit_form.nickname" />
      </div>
      <div class="form-row">
        <label class="form-label">{{ t('users.field_role') }}</label>
        <Select
          v-model="edit_form.role"
          :options="role_options"
          :disabled="edit_form.user_id === auth_store.user?.user_id"
        />
        <span v-if="edit_form.user_id === auth_store.user?.user_id" class="form-hint">{{
          t('users.self_role_hint')
        }}</span>
      </div>
    </Dialog>

    <!-- 重置密码 -->
    <Dialog
      v-model="reset_open"
      :title="t('users.reset_dialog_title')"
      :description="t('users.reset_dialog_description', { username: reset_form.username })"
      :confirm-text="t('users.reset_confirm')"
      :loading="submitting"
      @confirm="submit_reset"
    >
      <div class="form-row">
        <label class="form-label">{{ t('users.new_password_field') }}</label>
        <Input
          v-model="reset_form.password"
          type="password"
          :placeholder="t('users.new_password_placeholder')"
        />
      </div>
    </Dialog>

    <!-- 删除确认 -->
    <Dialog
      :model-value="Boolean(delete_target)"
      :title="t('users.delete_dialog_title')"
      :description="t('users.delete_dialog_description', { username: delete_target?.username })"
      :confirm-text="t('common.delete')"
      confirm-variant="danger"
      :loading="deleting"
      @update:model-value="(open) => !open && (delete_target = null)"
      @confirm="submit_delete"
    />
  </div>
</template>

<style scoped>
.table-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}

.search-box {
  position: relative;
  width: 280px;
}

.search-box .search-icon {
  position: absolute;
  left: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.search-box :deep(.ui-input) {
  padding-left: var(--space-8);
}

.col-actions {
  text-align: right;
  width: 80px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.user-text {
  display: flex;
  flex-direction: column;
}

.user-nickname {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
}

.user-username {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border);
}
</style>
