<script setup>
import { ref, onActivated, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/player'
import { useAuthStore } from '@/stores/auth'
import { use_toast } from '@/composables/use_toast'
import { use_async_action } from '@/composables/use_async_action'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Pagination from '@/components/ui/Pagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import PlayerHead from '@/components/PlayerHead.vue'

const player_store = usePlayerStore()
const auth_store = useAuthStore()
const { t } = useI18n()
const toast = use_toast()
const { run } = use_async_action()
const { binding_list, total, page, page_size, keyword, loading } = storeToRefs(player_store)

const search_text = ref('')

// 新增绑定
const bind_open = ref(false)
const bind_form = ref({ user: '', player: '' })
const binding = ref(false)

// 解绑确认
const unbind_target = ref(null) // { user, player }
const unbinding = ref(false)

onMounted(() => {
  refresh()
})

// 页面被 KeepAlive 缓存：切回时静默刷新绑定列表（首次挂载由 onMounted 负责，不重复请求）
let activated_once = false
onActivated(() => {
  if (!activated_once) {
    activated_once = true
    return
  }
  player_store.fetch_bindings().catch((error) => console.warn('fetch_bindings failed', error))
})

async function refresh() {
  await run(() => player_store.fetch_bindings(), t('players.fetch_failed'))
}

function handle_search() {
  player_store.set_keyword(search_text.value.trim())
  refresh()
}

function handle_page_change(target_page) {
  player_store.set_page(target_page)
  refresh()
}

async function submit_bind() {
  const { user, player } = bind_form.value
  if (!user.trim() || !player.trim()) {
    toast.error(t('players.bind_missing_fields'))
    return
  }
  const ok = await run(
    () => player_store.bind_player(user.trim(), player.trim()),
    t('players.bind_failed'),
    binding,
  )
  if (ok) {
    toast.success(t('players.bind_success'))
    bind_form.value = { user: '', player: '' }
    bind_open.value = false
  }
}

function confirm_unbind(user, player) {
  unbind_target.value = { user, player }
}

async function submit_unbind() {
  if (!unbind_target.value) return
  const ok = await run(
    () => player_store.unbind_player(unbind_target.value.user, unbind_target.value.player),
    t('players.unbind_failed'),
    unbinding,
  )
  if (ok) {
    toast.success(t('players.unbind_success'))
    unbind_target.value = null
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('players.page_title') }}</h1>
        <p class="page-desc">{{ t('players.page_description') }}</p>
      </div>
      <div class="page-actions">
        <Button v-if="auth_store.is_operator" variant="primary" @click="bind_open = true">
          <Icon icon="lucide:link" width="15" />
          {{ t('players.add_binding') }}
        </Button>
      </div>
    </div>

    <section class="card">
      <div class="table-toolbar">
        <form class="search-box" @submit.prevent="handle_search">
          <Icon icon="lucide:search" width="15" class="search-icon" />
          <Input
            v-model="search_text"
            :placeholder="t('players.search_placeholder')"
            @keydown.enter="handle_search"
          />
        </form>
        <Button variant="secondary" icon-only @click="refresh">
          <Icon icon="lucide:refresh-cw" width="15" />
        </Button>
      </div>

      <div v-if="loading && binding_list.length === 0" class="loading-block">
        <Spinner :size="18" /> {{ t('common.loading') }}
      </div>

      <EmptyState
        v-else-if="binding_list.length === 0"
        icon="lucide:users"
        :title="t('players.empty_title')"
        :description="
          keyword ? t('players.empty_search_result', { keyword }) : t('players.empty_default')
        "
      />

      <table v-else class="ui-table">
        <thead>
          <tr>
            <th>{{ t('players.column_user') }}</th>
            <th>{{ t('players.column_players') }}</th>
            <th>{{ t('players.column_time') }}</th>
            <th v-if="auth_store.is_operator" class="col-actions">
              {{ t('players.column_actions') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="binding in binding_list" :key="binding.user">
            <td>
              <span class="mono">{{ binding.user }}</span>
            </td>
            <td>
              <div class="player-tags">
                <span v-for="player in binding.players" :key="player" class="player-tag">
                  <PlayerHead :name="player" :size="16" />
                  {{ player }}
                  <button
                    v-if="auth_store.is_operator"
                    class="tag-remove"
                    :title="t('players.unbind_tooltip')"
                    @click="confirm_unbind(binding.user, player)"
                  >
                    <Icon icon="lucide:x" width="11" />
                  </button>
                </span>
              </div>
            </td>
            <td class="text-muted">{{ binding.bound_at || '—' }}</td>
            <td v-if="auth_store.is_operator" class="col-actions">
              <Button
                variant="ghost"
                size="sm"
                class="text-danger"
                @click="confirm_unbind(binding.user, binding.players[0])"
              >
                {{ t('players.unbind_action') }}
              </Button>
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

    <!-- 新增绑定 -->
    <Dialog
      v-model="bind_open"
      :title="t('players.add_dialog_title')"
      :description="t('players.add_dialog_description')"
      :confirm-text="t('players.bind_confirm')"
      :loading="binding"
      @confirm="submit_bind"
    >
      <div class="form-row">
        <label class="form-label">{{ t('players.field_user_label') }}</label>
        <Input v-model="bind_form.user" :placeholder="t('players.user_placeholder')" />
      </div>
      <div class="form-row">
        <label class="form-label">{{ t('players.field_player_label') }}</label>
        <Input v-model="bind_form.player" :placeholder="t('players.player_placeholder')" />
      </div>
    </Dialog>

    <!-- 解绑确认 -->
    <Dialog
      :model-value="Boolean(unbind_target)"
      :title="t('players.unbind_dialog_title')"
      :description="
        t('players.unbind_confirm_description', {
          user: unbind_target?.user,
          player: unbind_target?.player,
        })
      "
      :confirm-text="t('players.unbind_confirm')"
      confirm-variant="danger"
      :loading="unbinding"
      @update:model-value="(open) => !open && (unbind_target = null)"
      @confirm="submit_unbind"
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
  width: 100px;
}

.player-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.player-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px var(--space-2) 2px 4px;
  background: var(--surface-sunken);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  color: var(--text-muted);
  transition:
    background-color var(--transition),
    color var(--transition);
}

.tag-remove:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border);
}
</style>
