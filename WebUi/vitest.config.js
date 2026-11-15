import { fileURLToPath, URL } from 'node:url'
import { configDefaults, defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

/**
 * Vitest 配置：单元 / 组件测试。
 *
 * 独立的 vitest.config.js 而非放在 vite.config.js 中，
 * 避免开发构建插件（vue-devtools）进入测试链路。
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{js,mjs}', 'src/**/__tests__/**/*.{js,mjs}'],
    exclude: [...configDefaults.exclude],
    setupFiles: ['./vitest.setup.js'],
  },
})
