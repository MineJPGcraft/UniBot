import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const THEME_STORAGE_KEY = 'unibot_theme'

function initial_theme() {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(initial_theme())

  const is_dark = computed(() => theme.value === 'dark')

  function apply_theme() {
    document.documentElement.classList.toggle('dark', is_dark.value)
  }

  function set_theme(value) {
    theme.value = value === 'dark' ? 'dark' : 'light'
    localStorage.setItem(THEME_STORAGE_KEY, theme.value)
    apply_theme()
  }

  function toggle_theme() {
    set_theme(is_dark.value ? 'light' : 'dark')
  }

  // 与 index.html 内联脚本保持一致，兜底同步 class
  apply_theme()

  return { theme, is_dark, set_theme, toggle_theme }
})
