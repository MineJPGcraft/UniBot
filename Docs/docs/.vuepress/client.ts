import { h } from 'vue'
import { Layout } from 'vuepress-theme-plume/client'
import { defineClientConfig } from 'vuepress/client'
import PageContextMenu from 'vuepress-theme-plume/features/PageContextMenu.vue'

export default defineClientConfig({
  layouts: {
    Layout: h(Layout, null, {
      // 页面标题右侧添加「复制页面 / 以 Markdown 查看 / 在 ChatGPT 等平台中打开」
      // 依赖 @vuepress/plugin-llms，仅在构建后的生产包中可用
      'doc-title-after': () => h(PageContextMenu),
    }),
  },
})
