<script setup>
import { computed, onMounted, ref } from 'vue'
import { load as load_poem_sentence } from 'jinrishici'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useStatusStore } from '@/stores/status'
import { format_uptime, format_mb } from '@/utils/format'

const { t } = useI18n()
const status_store = useStatusStore()
const { status } = storeToRefs(status_store)

const uptime_text = computed(() => format_uptime(status.value?.uptime))

const poem = ref('')
const loading = ref(false)

function load_poem() {
  loading.value = true
  load_poem_sentence(
    (result) => {
      const { content, origin } = result.data
      poem.value = `${content}  —— 《${origin.title}》${origin.dynasty} · ${origin.author}`
      loading.value = false
    },
    () => {
      loading.value = false
    },
  )
}

onMounted(load_poem)
</script>

<template>
  <footer class="statusbar">
    <span>UniBot {{ status?.version || '—' }}</span>
    <span class="statusbar-sep">·</span>
    <span>{{ t('layout.statusbar_uptime', { uptime: uptime_text }) }}</span>
    <span class="statusbar-sep">·</span>
    <span>{{ t('layout.statusbar_memory', { memory: format_mb(status?.memory_mb) }) }}</span>
    <span class="statusbar-sep">·</span>
    <span>{{ t('layout.statusbar_cpu', { cpu: status?.cpu_percent ?? '—' }) }}</span>
    <span v-if="loading" class="statusbar-poem">{{ t('layout.statusbar_poem_loading') }}</span>
    <span
      v-else-if="poem"
      class="statusbar-poem"
      :title="t('layout.statusbar_poem_hint')"
      @click="load_poem()"
    >
      {{ poem }}
    </span>
  </footer>
</template>

<style scoped>
.statusbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: var(--statusbar-height);
  padding: 0 var(--space-6);
  background: var(--surface);
  border-top: 1px solid var(--border);
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}

.statusbar-sep {
  color: var(--border-strong);
}

.statusbar-poem {
  margin-left: auto;
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color 150ms ease-out;
}

.statusbar-poem:hover {
  color: var(--accent);
}
</style>
