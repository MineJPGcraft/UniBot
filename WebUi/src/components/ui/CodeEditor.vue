<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { HighlightStyle, StreamLanguage, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'
import { toml } from '@codemirror/legacy-modes/mode/toml'
import { properties } from '@codemirror/legacy-modes/mode/properties'
import { yaml } from '@codemirror/legacy-modes/mode/yaml'
import { storeToRefs } from 'pinia'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /** 高亮语言：toml | properties | yaml */
  language: { type: String, default: 'toml' },
  /** 只读模式：仅展示与选中，不可编辑（供 CodePanel 等复用） */
  readOnly: { type: Boolean, default: false },
  /** 最小高度，如 '0'、'200px'；默认 200px */
  minHeight: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const container = ref(null)
let view = null

const { is_dark } = storeToRefs(useThemeStore())

const container_style = computed(() => ({ minHeight: props.minHeight || '200px' }))

function language_ext() {
  const modes = { toml, properties, yaml }
  return StreamLanguage.define(modes[props.language] || toml)
}

// 语法高亮配色跟随主题（canvas 外可直接用 CSS 变量，但 lezer 高亮需字面量色值）
const highlight_styles = {
  light: HighlightStyle.define([
    { tag: tags.heading, color: '#18181b', fontWeight: '600' },
    { tag: tags.keyword, color: '#2563eb' },
    { tag: [tags.number, tags.bool, tags.null], color: '#d97706' },
    { tag: tags.string, color: '#16a34a' },
    { tag: [tags.comment, tags.lineComment], color: '#71717a', fontStyle: 'italic' },
  ]),
  dark: HighlightStyle.define([
    { tag: tags.heading, color: '#e7e7ea', fontWeight: '600' },
    { tag: tags.keyword, color: '#93c5fd' },
    { tag: [tags.number, tags.bool, tags.null], color: '#fcd34d' },
    { tag: tags.string, color: '#86efac' },
    { tag: [tags.comment, tags.lineComment], color: '#8b8b94', fontStyle: 'italic' },
  ]),
}

function highlight_ext() {
  return syntaxHighlighting(is_dark.value ? highlight_styles.dark : highlight_styles.light)
}

// 界面色走设计变量，随 html.dark 自动切换
const custom_theme = EditorView.theme({
  '&': {
    height: '100%',
    fontSize: '12px',
    backgroundColor: 'var(--surface-sunken)',
  },
  '.cm-scroller': {
    fontFamily: 'var(--font-mono)',
    lineHeight: '1.7',
  },
  '.cm-content': {
    caretColor: 'var(--text)',
  },
  '&.cm-focused': {
    outline: 'none',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--surface-sunken)',
    color: 'var(--text-muted)',
    border: 'none',
  },
  '.cm-activeLine': {
    backgroundColor: 'color-mix(in srgb, var(--text) 3%, transparent)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'color-mix(in srgb, var(--text) 4%, transparent)',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'var(--accent-soft)',
  },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--accent-soft)',
  },
  '.cm-cursor': {
    borderLeftColor: 'var(--accent)',
  },
  '.cm-tooltip': {
    backgroundColor: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
  },
})

function extensions() {
  return [
    basicSetup,
    language_ext(),
    highlight_ext(),
    EditorView.lineWrapping,
    custom_theme,
    ...(props.readOnly ? [EditorState.readOnly.of(true), EditorView.editable.of(false)] : []),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
    }),
  ]
}

onMounted(() => {
  const state = EditorState.create({
    doc: props.modelValue,
    extensions: extensions(),
  })
  view = new EditorView({ state, parent: container.value })
})

watch(
  () => props.modelValue,
  (value) => {
    if (view && value !== view.state.doc.toString()) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
    }
  },
)

watch(
  () => props.language,
  () => {
    if (view) {
      view.dispatch({ effects: EditorState.reconfigure.of(extensions()) })
    }
  },
)

watch(is_dark, () => {
  if (view) {
    view.dispatch({ effects: EditorState.reconfigure.of(extensions()) })
  }
})

onBeforeUnmount(() => view?.destroy())
</script>

<template>
  <div ref="container" class="code-editor" :style="container_style" />
</template>

<style scoped>
.code-editor {
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-sunken);
}

/* 覆盖全局 ::selection 的白字，保证选中文本在浅色高亮下可读 */
.code-editor ::selection {
  background: var(--accent-soft);
  color: var(--text);
}
</style>
