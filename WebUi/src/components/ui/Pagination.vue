<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Icon } from '@iconify/vue'
import {
  PaginationRoot,
  PaginationList,
  PaginationListItem,
  PaginationEllipsis,
  PaginationFirst,
  PaginationPrev,
  PaginationNext,
  PaginationLast,
} from 'reka-ui'
import Button from './Button.vue'
import Input from './Input.vue'

const { t } = useI18n()

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
})

const emit = defineEmits(['page-change'])

const total_pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const jump_value = ref('')

function on_page_change(value) {
  emit('page-change', value)
}

function jump() {
  const target = Number(jump_value.value)
  jump_value.value = ''
  if (!target || target < 1 || target > total_pages.value) return
  emit('page-change', target)
}
</script>

<template>
  <div class="ui-pagination">
    <PaginationRoot
      :page="page"
      :total="total"
      :items-per-page="pageSize"
      show-edges
      @update:page="on_page_change"
    >
      <PaginationList v-slot="{ items }" class="ui-pagination-list">
        <PaginationFirst class="ui-pagination-btn" :title="t('common.page_first')">
          <Icon icon="lucide:chevrons-left" width="14" />
        </PaginationFirst>
        <PaginationPrev class="ui-pagination-btn" :title="t('common.page_prev')">
          <Icon icon="lucide:chevron-left" width="14" />
        </PaginationPrev>

        <template v-for="(item, index) in items">
          <PaginationListItem
            v-if="item.type === 'page'"
            :key="item.value"
            :value="item.value"
            class="ui-pagination-btn"
          >
            {{ item.value }}
          </PaginationListItem>
          <PaginationEllipsis
            v-else
            :key="`ellipsis-${index}`"
            :index="index"
            class="ui-pagination-ellipsis"
          >
            …
          </PaginationEllipsis>
        </template>

        <PaginationNext class="ui-pagination-btn" :title="t('common.page_next')">
          <Icon icon="lucide:chevron-right" width="14" />
        </PaginationNext>
        <PaginationLast class="ui-pagination-btn" :title="t('common.page_last')">
          <Icon icon="lucide:chevrons-right" width="14" />
        </PaginationLast>
      </PaginationList>
    </PaginationRoot>

    <div class="ui-pagination-jump">
      <Input
        v-model="jump_value"
        type="number"
        min="1"
        :max="total_pages"
        :placeholder="t('common.page_number')"
        class="ui-pagination-input"
        @keydown.enter="jump"
      />
      <Button variant="secondary" size="sm" @click="jump">{{ t('common.page_jump') }}</Button>
    </div>
  </div>
</template>

<style scoped>
.ui-pagination {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* reka-ui PaginationList 渲染为 nav 内的容器 */
.ui-pagination-list {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* 统一页码按钮 / 首页 / 末页 / 上一页 / 下一页 的样式，reka-ui 均渲染为 <button> */
.ui-pagination-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  min-width: 28px;
  padding: 0 var(--space-1);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
  user-select: none;
  transition:
    background-color var(--transition),
    border-color var(--transition),
    color var(--transition);
}

.ui-pagination-btn:hover:not(:disabled) {
  border-color: var(--border-strong);
  color: var(--text);
}

.ui-pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 当前页高亮，reka-ui 通过 data-selected 标记选中项 */
.ui-pagination-btn[data-selected] {
  background: var(--accent);
  border-color: var(--accent);
  color: #ffffff;
  cursor: default;
}

.ui-pagination-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.ui-pagination-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  min-width: 28px;
  color: var(--text-muted);
  font-size: var(--text-xs);
  user-select: none;
}

.ui-pagination-jump {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-1);
}

.ui-pagination-input {
  width: 64px;
}

/* 与 size="sm" 按钮（28px）保持高度一致，并隐藏数字输入框自带的步进箭头。
   注意：class 合并后 .ui-pagination-input 与 .ui-input 是同一元素，必须用直接选择器 */
input.ui-pagination-input {
  height: 28px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
  appearance: textfield;
  -moz-appearance: textfield;
}

input.ui-pagination-input::-webkit-outer-spin-button,
input.ui-pagination-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
