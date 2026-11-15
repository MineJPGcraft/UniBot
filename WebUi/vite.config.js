import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

/**
 * 依赖分包策略：把体积大且按页面使用的依赖拆成独立 chunk，
 * 避免它们互相放大单个页面 chunk（统计页的图表、配置页的编辑器）。
 *
 * ⚠️ Vite 8 基于 Rolldown，`rollupOptions.output.manualChunks` 只是兼容层，
 * 它默认递归吸纳依赖（`includeDependenciesRecursively`），会把 Vue 运行时
 * 塞进图表 chunk，导致入口反向静态引用 ECharts（首屏多下 655 kB）。
 * 因此这里使用 Rolldown 原生的 `codeSplitting.groups` 并显式关闭递归。
 */
const VENDOR_GROUPS = [
  {
    // 图表库：仅统计页使用，必须保持可懒加载
    name: 'charts',
    test: /node_modules[\\/](echarts|zrender|vue-echarts)[\\/]/,
    priority: 30,
  },
  {
    // 代码编辑器：仅配置页使用
    name: 'editor',
    test: /node_modules[\\/](@codemirror|codemirror|@lezer|@marijn|style-mod|w3c-keyname|crelt)[\\/]/,
    priority: 30,
  },
  {
    // 无障碍组件库及其浮层依赖
    name: 'reka',
    test: /node_modules[\\/](reka-ui|@floating-ui|@vueuse|aria-hidden|defu|ohash)[\\/]/,
    priority: 20,
  },
  {
    // Vue 全家桶：入口即需要，单独成块便于长期缓存
    name: 'vue-vendor',
    test: /node_modules[\\/](vue|@vue|vue-router|pinia|vue-i18n|@intlify)[\\/]/,
    priority: 20,
  },
]

// https://vite.dev/config/
export default defineConfig({
  base: '/webui/',
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/webui/api': 'http://localhost:8000',
      // 注意：不代理 /webui/ws，WebSocket 由前端直连后端（避免 Bun 下 http-proxy 兼容问题）
      // 直连地址见 src/composables/use_websocket.js 的 build_url()
    },
  },
  build: {
    // 分包后单块上限：图表库约 490 kB、编辑器约 400 kB，其余均远小于此值
    chunkSizeWarningLimit: 600,
    rolldownOptions: {
      output: {
        codeSplitting: {
          includeDependenciesRecursively: false,
          groups: VENDOR_GROUPS,
        },
      },
    },
  },
})
