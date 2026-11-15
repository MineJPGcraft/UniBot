<script setup>
/**
 * 消息值编辑器：基于 contenteditable 的「文本 + 原子占位符标签」编辑器。
 *
 * - 占位符以不可编辑的行内标签混排在文本中，可拖动调整位置，也可随文本一起复制粘贴；
 * - 方向键整体跳过标签、剪切不拆开标签、删除键整体删除标签，方便连续输入；
 * - 可切换「占位符 / 原文」两种视图：原文视图直接编辑 `{name}` 原始文本；
 * - 输出即真正的消息模板（`{name}` 形式）。
 */
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { use_message_editor } from '@/composables/use_message_editor'

const model = defineModel({ type: String, default: '' })

const props = defineProps({
  /** 该消息可用的占位符名（不含花括号） */
  placeholders: { type: Array, default: () => [] },
  placeholderHint: { type: String, default: '' },
})

const { raw_mode } = use_message_editor()

// 仅匹配非空占位符名，避免 `{}` 被渲染成不可见且删不掉的空标签。
const TAG_PATTERN = /\{([a-zA-Z0-9_.]+)\}/g

const editor = ref(null)
const root = ref(null)
const dragging_name = ref('')
/** 拖拽落点指示线的内联样式（display: none 即隐藏） */
const indicator_style = ref({ display: 'none' })
/** 正在拖动的既有标签元素（内部拖动时用于移动而非复制） */
let dragging_element = null
/** 编辑器内上次光标位置（点击占位符时编辑器已失焦，用它定位插入点） */
let saved_range = null
/** 指示线更新的待处理坐标与动画帧句柄（按帧节流高频 dragover） */
let pending_point = null
let frame_id = 0

/** 创建不可编辑的原子占位符标签。 */
function create_tag(name) {
  const element = document.createElement('span')
  element.className = 'ph-tag'
  element.contentEditable = 'false'
  element.draggable = true
  element.dataset.placeholder = name
  element.textContent = `{${name}}`
  element.addEventListener('dragstart', (event) => start_tag_drag(name, event))
  element.addEventListener('dragend', end_drag)
  return element
}

/** 把 `{name}` 原始文本解析为「文本节点 + 标签元素」的文档片段。 */
function fragment_from_text(text) {
  const fragment = document.createDocumentFragment()
  let cursor = 0
  TAG_PATTERN.lastIndex = 0
  let match
  while ((match = TAG_PATTERN.exec(text))) {
    if (match.index > cursor)
      fragment.append(document.createTextNode(text.slice(cursor, match.index)))
    fragment.append(create_tag(match[1]))
    cursor = match.index + match[0].length
  }
  if (cursor < text.length) fragment.append(document.createTextNode(text.slice(cursor)))
  return fragment
}

/** contenteditable 会把空格写成 nbsp，落盘前统一还原为普通空格。 */
function normalize(text) {
  return text.replace(/\u00a0/g, ' ')
}

/** 读取编辑器纯文本（标签还原为 `{name}`；nbsp 归一化为普通空格）。 */
function text_from_html() {
  const clone = editor.value.cloneNode(true)
  for (const element of clone.querySelectorAll('[data-placeholder]')) {
    element.replaceWith(document.createTextNode(`{${element.dataset.placeholder}}`))
  }
  return normalize(clone.textContent)
}

/** 按当前视图读取编辑器纯文本，读写与比较统一经此入口。 */
function current_text() {
  if (raw_mode.value) return normalize(editor.value.innerText)
  return text_from_html()
}

/** 按当前视图渲染编辑器内容。 */
function render_content() {
  if (raw_mode.value) {
    editor.value.textContent = model.value
    return
  }
  editor.value.replaceChildren(fragment_from_text(model.value))
}

function on_input() {
  const text = current_text()
  if (text !== model.value) model.value = text
}

// 切换全局视图模式时重建内容（光标位置失效，直接丢弃）。
watch(raw_mode, async () => {
  saved_range = null
  await nextTick()
  render_content()
})

// 外部值变化（恢复默认、切换语言等）时重建内容；自身编辑不触发重建，避免光标跳动。
watch(model, (value) => {
  if (!editor.value || value === current_text()) return
  render_content()
})

onMounted(render_content)
onUnmounted(() => cancelAnimationFrame(frame_id))

// ===== 选区工具 =====

function set_selection(range) {
  const selection = window.getSelection()
  selection.removeAllRanges()
  selection.addRange(range)
}

function place_caret_before(node) {
  const range = document.createRange()
  range.setStartBefore(node)
  range.collapse(true)
  set_selection(range)
}

function place_caret_after(node) {
  const range = document.createRange()
  range.setStartAfter(node)
  range.collapse(true)
  set_selection(range)
}

/** 记住编辑器内的光标位置，供失焦后（点击占位符）定位插入点。 */
function remember_selection() {
  const selection = window.getSelection()
  if (!selection?.rangeCount) return
  const range = selection.getRangeAt(0)
  if (!editor.value?.contains(range.startContainer)) return
  saved_range = range.cloneRange()
}

/** 取可用的插入区域：优先编辑器内实时选区，否则回退上次记录的光标。 */
function insert_range() {
  const selection = window.getSelection()
  const live = selection?.rangeCount ? selection.getRangeAt(0) : null
  if (live && editor.value.contains(live.startContainer)) return live
  if (saved_range && editor.value.contains(saved_range.startContainer)) return saved_range
  return null
}

/** 光标紧贴某标签侧边时返回该标签（`side` 为标签相对光标的位置）。 */
function tag_at_caret(selection, side) {
  if (!selection.isCollapsed || selection.rangeCount === 0) return null
  const node = selection.anchorNode
  if (node?.nodeType !== Node.TEXT_NODE) return null
  const edge = side === 'before' ? 0 : node.length
  if (selection.anchorOffset !== edge) return null
  const sibling = side === 'before' ? node.previousSibling : node.nextSibling
  return sibling?.dataset?.placeholder !== undefined ? sibling : null
}

// ===== 键盘：整体跳过 / 删除标签 =====

function handle_keydown(event) {
  if (raw_mode.value) return
  // 输入法组合中（如中文拼音）的回车是“上屏”，不能拦截。
  if (event.key === 'Enter' && !event.isComposing) {
    event.preventDefault()
    return
  }
  const selection = window.getSelection()
  if (!selection) return

  if (event.key === 'ArrowLeft') {
    const tag = tag_at_caret(selection, 'before')
    if (!tag) return
    event.preventDefault()
    place_caret_before(tag)
    return
  }

  if (event.key === 'ArrowRight') {
    const tag = tag_at_caret(selection, 'after')
    if (!tag) return
    event.preventDefault()
    place_caret_after(tag)
    return
  }

  if (event.key === 'Backspace') {
    const tag = tag_at_caret(selection, 'before')
    if (!tag) return
    event.preventDefault()
    remove_tag(tag)
    return
  }

  if (event.key === 'Delete') {
    const tag = tag_at_caret(selection, 'after')
    if (!tag) return
    event.preventDefault()
    remove_tag(tag)
  }
}

/** 删除标签并把光标落在其原位（无后续节点则落在文末）。 */
function remove_tag(tag) {
  const next = tag.nextSibling
  tag.remove()
  if (next) {
    place_caret_before(next)
  } else {
    const range = document.createRange()
    range.selectNodeContents(editor.value)
    range.collapse(false)
    set_selection(range)
  }
  on_input()
}

// ===== 拖拽 =====

function start_tag_drag(name, event) {
  dragging_element = event.currentTarget
  dragging_name.value = name
  event.dataTransfer?.setData('text/plain', `{${name}}`)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  event.currentTarget.classList.add('ph-tag--dragging')
}

function start_palette_drag(name, event) {
  const element = event.currentTarget
  dragging_element = null
  dragging_name.value = name
  event.dataTransfer?.setData('text/plain', `{${name}}`)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'copy'
    // 拖拽镜像用原标签，拖动时它不会从面板消失（复制语义）。
    if (element) {
      event.dataTransfer.setDragImage(element, element.offsetWidth / 2, element.offsetHeight / 2)
    }
  }
}

function end_drag(event) {
  const element = event?.currentTarget
  if (element?.dataset?.placeholder !== undefined) element.classList.remove('ph-tag--dragging')
  dragging_name.value = ''
  dragging_element = null
  hide_indicator()
}

function on_dragover(event) {
  if (!dragging_name.value) return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = dragging_element ? 'move' : 'copy'
  update_indicator(event.clientX, event.clientY)
}

/** 拖出编辑器时收起指示线（在子节点间移动不算离开）。 */
function on_dragleave(event) {
  if (!dragging_name.value) return
  if (editor.value?.contains(event.relatedTarget)) return
  hide_indicator()
}

/** 折叠区域的插入光标矩形；部分浏览器对折叠区域返回空矩形，用临时标记测量兜底。 */
function caret_rect(range) {
  const collapsed = range.cloneRange()
  collapsed.collapse(true)
  const rect = collapsed.getBoundingClientRect()
  if (rect.height) return rect
  const marker = document.createElement('span')
  marker.textContent = '\u200b'
  collapsed.insertNode(marker)
  const measured = marker.getBoundingClientRect()
  const parent = marker.parentNode
  marker.remove()
  parent?.normalize?.()
  return measured
}

/** 按鼠标坐标更新拖拽落点指示线（按帧节流，避免高频 dragover 抖动）。 */
function update_indicator(x, y) {
  pending_point = { x, y }
  if (frame_id) return
  frame_id = requestAnimationFrame(() => {
    frame_id = 0
    const point = pending_point
    if (!point || !dragging_name.value) return
    const range = range_from_point(point.x, point.y)
    if (!range) {
      hide_indicator()
      return
    }
    const caret = caret_rect(range)
    const base = root.value.getBoundingClientRect()
    // 绝对定位相对包含块的 padding box，减掉边框宽度才能与鼠标落点对齐。
    indicator_style.value = {
      display: 'block',
      left: `${caret.left - base.left - root.value.clientLeft}px`,
      top: `${caret.top - base.top - root.value.clientTop}px`,
      height: `${Math.max(caret.height, 16)}px`,
    }
  })
}

function hide_indicator() {
  pending_point = null
  if (indicator_style.value.display !== 'none') indicator_style.value = { display: 'none' }
}

/** 修正插入区域：编辑器外返回 null；落在标签上则改到标签之后。 */
function clamp_range(range) {
  if (!range || !editor.value.contains(range.startContainer)) return null
  const holder =
    range.startContainer.nodeType === Node.TEXT_NODE
      ? range.startContainer.parentElement
      : range.startContainer
  const tag_element = holder?.closest?.('[data-placeholder]')
  if (!tag_element) return range
  const after = document.createRange()
  after.setStartAfter(tag_element)
  after.collapse(true)
  return after
}

/**
 * 由鼠标坐标求编辑器内的插入区域（标准 `caretPositionFromPoint`）。
 * 不支持该 API 的浏览器返回 null，拖拽时不显示落点指示线。
 */
function range_from_point(x, y) {
  if (typeof document.caretPositionFromPoint !== 'function') return null
  const position = document.caretPositionFromPoint(x, y)
  if (!position) return null
  const range = document.createRange()
  range.setStart(position.offsetNode, position.offset)
  range.collapse(true)
  return clamp_range(range)
}

function on_drop(event) {
  if (!dragging_name.value) return
  event.preventDefault()
  hide_indicator()
  const range = range_from_point(event.clientX, event.clientY)
  if (!range) {
    end_drag(event)
    return
  }
  const tag = dragging_element?.isConnected ? dragging_element : create_tag(dragging_name.value)
  range.deleteContents()
  range.insertNode(tag)
  place_caret_after(tag)
  dragging_element = null
  dragging_name.value = ''
  on_input()
}

/** 点击占位符：插入到光标处（无有效光标则追加到末尾）。 */
function insert_placeholder(name) {
  if (raw_mode.value) {
    insert_plain_text(`{${name}}`)
    editor.value.focus()
    return
  }
  const tag = create_tag(name)
  const range = insert_range()
  if (range) {
    range.deleteContents()
    range.insertNode(tag)
  } else {
    editor.value.append(tag)
  }
  editor.value.focus()
  place_caret_after(tag)
  on_input()
}

/** 在光标处插入纯文本（原文视图用；无有效光标则追加到末尾）。 */
function insert_plain_text(text) {
  const range = insert_range()
  if (!range) {
    editor.value.append(document.createTextNode(text))
    on_input()
    return
  }
  range.deleteContents()
  const node = document.createTextNode(text)
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  set_selection(range)
  on_input()
}

/** 粘贴纯文本时把 `{name}` 还原为标签（占位符视图）。 */
function on_paste(event) {
  if (raw_mode.value) return
  const text = event.clipboardData?.getData('text/plain')
  if (!text) return
  event.preventDefault()
  const fragment = fragment_from_text(text)
  const nodes = [...fragment.childNodes]
  const selection = window.getSelection()
  const range = selection?.rangeCount ? selection.getRangeAt(0) : null
  if (range && editor.value.contains(range.startContainer)) {
    range.deleteContents()
    range.insertNode(fragment)
  } else {
    editor.value.append(fragment)
  }
  const last = nodes[nodes.length - 1]
  if (last) place_caret_after(last)
  on_input()
}

/** 把 DOM 节点转为纯文本（标签还原为 `{name}`）。 */
function text_from_nodes(nodes) {
  const holder = document.createElement('div')
  for (const node of nodes) holder.append(node.cloneNode(true))
  for (const element of holder.querySelectorAll('[data-placeholder]'))
    element.replaceWith(document.createTextNode(`{${element.dataset.placeholder}}`))
  return normalize(holder.textContent)
}

/** 取编辑器内非折叠选区；无有效选区返回 null。 */
function selected_range() {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null
  const range = selection.getRangeAt(0)
  return editor.value.contains(range.commonAncestorContainer) ? range : null
}

/** 复制：把选中内容（标签还原为 `{name}`）写入剪贴板。 */
function on_copy(event) {
  if (raw_mode.value) return
  const range = selected_range()
  if (!range) return
  const text = text_from_nodes([...range.cloneContents().childNodes])
  if (!text) return
  event.preventDefault()
  event.clipboardData?.setData('text/plain', text)
}

/** 剪切：写入剪贴板后删除选区，并把光标落在删除处。 */
function on_cut(event) {
  if (raw_mode.value) return
  const range = selected_range()
  if (!range) return
  const text = text_from_nodes([...range.cloneContents().childNodes])
  if (!text) return
  event.preventDefault()
  event.clipboardData?.setData('text/plain', text)
  range.deleteContents()
  range.collapse(true)
  set_selection(range)
  on_input()
}

/** 占位符标签的展示文本（含花括号）。 */
function tag_label(name) {
  return `{${name}}`
}
</script>

<template>
  <div ref="root" class="value-editor">
    <div
      ref="editor"
      class="value-surface"
      :class="{ 'value-surface--raw': raw_mode }"
      contenteditable="true"
      spellcheck="false"
      @input="on_input"
      @keydown="handle_keydown"
      @keyup="remember_selection"
      @mouseup="remember_selection"
      @paste="on_paste"
      @copy="on_copy"
      @cut="on_cut"
      @dragover="on_dragover"
      @dragleave="on_dragleave"
      @drop="on_drop"
    />

    <div class="drop-caret" :style="indicator_style" />

    <div v-if="placeholders.length" class="value-palette">
      <span class="value-palette-label">{{ placeholderHint }}</span>
      <span
        v-for="name in placeholders"
        :key="name"
        class="ph-tag ph-tag--palette"
        draggable="true"
        :class="{ 'ph-tag--dragging': dragging_name === name }"
        @dragstart="start_palette_drag(name, $event)"
        @dragend="end_drag"
        @click="insert_placeholder(name)"
      >
        <Icon icon="lucide:plus" width="11" />
        <span>{{ tag_label(name) }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.value-editor {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

/* 拖拽落点指示线：跟随鼠标位置的竖线 + 顶部圆头 */
.drop-caret {
  position: absolute;
  z-index: 2;
  width: 2px;
  border-radius: 1px;
  background: var(--accent);
  pointer-events: none;
}

.drop-caret::before {
  content: '';
  position: absolute;
  top: -3px;
  left: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  transform: translateX(-50%);
}

.value-surface {
  min-height: 32px;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: var(--text-sm);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  outline: none;
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.value-surface:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}

.value-surface--raw {
  font-family: var(--font-mono);
}

/* 占位符标签由 JS 动态创建，需 :deep 才能命中作用域样式 */
.value-editor :deep(.ph-tag) {
  display: inline-block;
  padding: 0 var(--space-1);
  margin: 0 1px;
  border-radius: 3px;
  background: var(--accent-soft);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  line-height: 1.6;
  white-space: nowrap;
  cursor: grab;
}

.value-editor :deep(.ph-tag--dragging) {
  opacity: 0.4;
}

.value-palette {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  padding-top: var(--space-1);
  border-top: 1px dashed var(--border);
}

.value-palette-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.value-editor .ph-tag--palette {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text-secondary);
}

.value-editor .ph-tag--palette:hover {
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
