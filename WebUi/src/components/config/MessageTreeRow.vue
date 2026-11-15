<script setup>
/**
 * 消息树叶片行：显示「键名 + 状态标标 + 恢复默认」与对应的值编辑器。
 *
 * 状态标标分两种：未保存改动（橙色「已修改」）/ 已保存的覆盖（蓝色「已覆盖」）；
 * 值编辑器按类型分流：字符串用 MessageValueEditor（占位符可拖拽），
 * 字符串列表用行内列表编辑；草稿值由父级统一管理。
 */
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_list_keys } from '@/composables/use_list_keys'
import MessageValueEditor from '@/components/config/MessageValueEditor.vue'
import Input from '@/components/ui/Input.vue'
import { message_modified, message_pending, message_value } from '@/utils/message_tree'

const props = defineProps({
  /** 叶子消息项：{ key, value, base_value, is_list, placeholders } */
  item: { type: Object, required: true },
  /** 草稿：键 → 草稿值 */
  draft: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update'])

const { t } = useI18n()

const list_keys = use_list_keys()

function current() {
  return message_value(props.item, props.draft)
}

function is_modified() {
  return message_modified(props.item, props.draft)
}

/** 是否有未保存的草稿改动（相对服务端生效值） */
function is_pending() {
  return message_pending(props.item, props.draft)
}

function update(value) {
  emit('update', props.item.key, value)
}

function remove_list_item(index) {
  list_keys.remove(index)
  const list = [...current()]
  list.splice(index, 1)
  update(list)
}

function add_list_item() {
  update([...current(), ''])
}

function update_list_item(index, value) {
  update(current().map((entry, i) => (i === index ? value : entry)))
}
</script>

<template>
  <div class="message-row">
    <div class="message-row-head">
      <code class="message-key">{{ item.key }}</code>
      <span v-if="is_pending()" class="message-badge">
        {{ t('config_view.messages_modified') }}
      </span>
      <span v-else-if="is_modified()" class="message-badge message-badge--saved">
        {{ t('config_view.messages_override') }}
      </span>
      <button
        v-if="is_modified()"
        type="button"
        class="message-reset"
        :title="t('config_view.messages_reset')"
        @click="update(item.base_value)"
      >
        <Icon icon="lucide:rotate-ccw" width="13" />
      </button>
    </div>

    <div v-if="item.is_list" class="list-editor">
      <div v-for="(entry, index) in current()" :key="list_keys.key_for(index)" class="list-row">
        <Input :model-value="entry" @update:model-value="(val) => update_list_item(index, val)" />
        <button type="button" class="list-remove" @click="remove_list_item(index)">
          <Icon icon="lucide:minus" width="14" />
        </button>
      </div>
      <button type="button" class="list-add" @click="add_list_item">
        <Icon icon="lucide:plus" width="13" />
        {{ t('config_view.messages_add_item') }}
      </button>
    </div>

    <MessageValueEditor
      v-else
      :model-value="current()"
      :placeholders="item.placeholders"
      :placeholder-hint="t('config_view.messages_placeholder_hint')"
      @update:model-value="update"
    />
  </div>
</template>

<style scoped>
.message-row {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.message-row-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.message-key {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-badge {
  padding: 0 var(--space-2);
  height: 18px;
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius);
  background: var(--warning-soft);
  color: var(--warning);
  font-size: var(--text-xs);
  font-weight: 500;
}

/* 已保存的覆盖：安静的蓝色标标，与未保存的橙色「已修改」区分 */
.message-badge--saved {
  background: var(--accent-soft);
  color: var(--accent);
}

.message-reset {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius);
  color: var(--text-muted);
  cursor: pointer;
}

.message-reset:hover {
  background: var(--hover);
  color: var(--text);
}

.list-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.list-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.list-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius);
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
}

.list-remove:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.list-add {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  align-self: flex-start;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  color: var(--accent);
  cursor: pointer;
}

.list-add:hover {
  background: var(--accent-soft);
}
</style>
