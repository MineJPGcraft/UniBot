<script setup>
/**
 * 对象数组字段控件（卡片列表）。
 *
 * 每项为一张可折叠卡片：头部是「标题 + 扫码绑定 + 上移 / 下移 / 删除」，
 * 主体按元素 schema 的子字段递归渲染 `SchemaField`。
 *
 * 卡片折叠状态以「列表稳定 key」为索引，新增卡片默认展开、扫码成功后展开，
 * 使行内状态跟随条目本身而非下标。
 */
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import { use_list_keys } from '@/composables/use_list_keys'
import { clone, default_value, dereference, effective_schema } from '@/utils/schema_form'
import Button from '../Button.vue'
import QrScanDialog from '../QrScanDialog.vue'
import SchemaField from '../SchemaField.vue'

const props = defineProps({
  /** 数组字段定义（含 `items` / `x-item-title` / `x-item-placeholder` / `x-qr-connect`） */
  schema: { type: Object, required: true },
  modelValue: { type: Array, default: () => [] },
  /** 所属根 schema（解析 `items.$ref` 用） */
  rootSchema: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const list_keys = use_list_keys()
/** 卡片折叠状态：键为其列表稳定 key，未记录时视为折叠 */
const collapsed_items = reactive({})
const qr_index = ref(null)

const items = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))

/** 数组元素定义（`items.$ref` 经根 schema 解引用为 `$defs` 中的对象定义） */
const item_schema = computed(() => {
  const raw_items = props.schema.items
  if (!raw_items) return null
  const target = dereference(props.rootSchema, raw_items) || raw_items
  return effective_schema(target) || target
})

const item_properties = computed(() => item_schema.value?.properties || {})

/** 数组元素标题：`x-item-placeholder` 指定的字段值，缺失时回落 `x-item-title` + 序号 */
function item_title(item, index) {
  const placeholder = props.schema['x-item-placeholder']
  const title = placeholder ? String(item?.[placeholder] ?? '') : ''
  const fallback = props.schema['x-item-title'] || t('ui.form_editor_item_fallback')
  return title || `${fallback} ${index + 1}`
}

function is_collapsed(index) {
  return collapsed_items[list_keys.key_for(index)] !== false
}

function set_collapsed(index, collapsed) {
  collapsed_items[list_keys.key_for(index)] = collapsed
}

function toggle_item(index) {
  set_collapsed(index, !is_collapsed(index))
}

function add_item() {
  const template = {}
  for (const [name, child] of Object.entries(item_properties.value)) {
    template[name] = default_value(child, name)
  }
  emit('update:modelValue', [...items.value, template])
  // 新卡片默认展开，便于直接填写
  set_collapsed(items.value.length, false)
}

function remove_item(index) {
  const next = clone(items.value)
  next.splice(index, 1)
  list_keys.remove(index)
  emit('update:modelValue', next)
}

function move_item(index, offset) {
  const target = index + offset
  const next = clone(items.value)
  if (target < 0 || target >= next.length) return
  ;[next[index], next[target]] = [next[target], next[index]]
  list_keys.move(index, target)
  emit('update:modelValue', next)
}

function update_field(index, name, value) {
  const next = clone(items.value)
  next[index][name] = value
  emit('update:modelValue', next)
}

/** 扫码绑定配置（QQ 机器人卡片），无此配置时不显示入口 */
const qr_connect = computed(() => props.schema['x-qr-connect'] || null)

function apply_qr_result(index, credentials) {
  const config = qr_connect.value
  if (!config) return
  const next = clone(items.value)
  const item = next[index] || {}
  if (config.id_key && credentials.app_id) item[config.id_key] = credentials.app_id
  if (config.secret_key && credentials.app_secret) item[config.secret_key] = credentials.app_secret
  next[index] = item
  emit('update:modelValue', next)
  // 扫码成功后展开卡片，方便补充其余字段
  set_collapsed(index, false)
}
</script>

<template>
  <div class="field-object-list">
    <div v-for="(item, index) in items" :key="list_keys.key_for(index)" class="field-object-item">
      <div
        class="field-object-head"
        :class="{ 'field-object-head--collapsed': is_collapsed(index) }"
      >
        <button class="field-object-title" type="button" @click="toggle_item(index)">
          <Icon
            :icon="is_collapsed(index) ? 'lucide:chevron-down' : 'lucide:chevron-up'"
            width="14"
            class="field-object-chevron"
          />
          {{ item_title(item, index) }}
        </button>
        <div class="field-object-actions">
          <Button
            v-if="qr_connect"
            variant="ghost"
            size="sm"
            icon-only
            :disabled="disabled"
            :title="t('ui.form_editor_qr_bind_title')"
            @click="qr_index = index"
          >
            <Icon icon="lucide:qr-code" width="14" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon-only
            :disabled="disabled || index === 0"
            :title="t('ui.form_editor_move_up')"
            @click="move_item(index, -1)"
          >
            <Icon icon="lucide:arrow-up" width="14" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon-only
            :disabled="disabled || index === items.length - 1"
            :title="t('ui.form_editor_move_down')"
            @click="move_item(index, 1)"
          >
            <Icon icon="lucide:arrow-down" width="14" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon-only
            :disabled="disabled"
            :title="t('ui.form_item_remove')"
            @click="remove_item(index)"
          >
            <Icon icon="lucide:trash-2" width="14" />
          </Button>
        </div>
      </div>
      <div v-show="!is_collapsed(index)" class="field-object-body">
        <div v-for="(child, name) in item_properties" :key="name" class="field-subfield">
          <div class="field-subfield-label">{{ child.title || name }}</div>
          <p v-if="child.description" class="field-subfield-desc">{{ child.description }}</p>
          <SchemaField
            :schema="child"
            :field-key="name"
            :root-schema="rootSchema"
            :model-value="item?.[name]"
            :disabled="disabled"
            @update:model-value="(value) => update_field(index, name, value)"
          />
        </div>
      </div>
      <QrScanDialog
        v-if="qr_connect"
        :open="qr_index === index"
        :source="qr_connect.source || ''"
        @success="(credentials) => apply_qr_result(index, credentials)"
        @update:open="(value) => (qr_index = value ? index : null)"
      />
    </div>
    <Button
      variant="secondary"
      size="xs"
      class="field-add"
      :class="{ 'field-add--empty': items.length === 0 }"
      :disabled="disabled"
      @click="add_item"
    >
      <Icon icon="lucide:plus" width="13" />
      {{
        t('ui.form_add_named_item', {
          name: schema['x-item-title'] || t('ui.form_editor_item_fallback'),
        })
      }}
    </Button>
  </div>
</template>

<style scoped>
.field-object-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

/* 对象数组卡片 */
.field-object-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.field-object-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border);
  transition: border-color var(--transition);
}

/* 折叠态：标题与操作栏紧贴，去掉分隔线 */
.field-object-head--collapsed {
  padding-bottom: 0;
  border-bottom: none;
}

.field-object-title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  padding: 2px 4px;
  margin-left: -4px;
  border: none;
  border-radius: var(--radius);
  background: none;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: background-color var(--transition);
}

.field-object-title:hover {
  background: var(--surface);
}

.field-object-chevron {
  flex: 0 0 auto;
  color: var(--text-muted);
  transition: color var(--transition);
}

.field-object-title:hover .field-object-chevron {
  color: var(--text);
}

.field-object-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.field-object-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.field-subfield {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.field-subfield-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-muted);
}

.field-subfield-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

.field-subfield :deep(.ui-input),
.field-subfield :deep(.ui-textarea),
.field-subfield :deep(.ui-select-trigger) {
  width: 100%;
}

.field-add {
  align-self: flex-end;
}

.field-add--empty {
  align-self: flex-end;
  margin: var(--space-1) 0;
}
</style>
