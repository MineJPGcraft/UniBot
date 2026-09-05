import { defineUserConfig } from 'vuepress'
import { viteBundler } from '@vuepress/bundler-vite'
import { plumeTheme } from 'vuepress-theme-plume'

export default defineUserConfig({
  // 默认语言
  lang: 'zh-CN',
  title: 'Minecraft UniBot 文档',
  description: 'Minecraft UniBot 是开源免费的 Minecraft 群服互通机器人：支持 QQ、QQ 频道、Telegram、Discord、KOOK、DoDo 等聊天平台与多台 MC 服务器实时互通，跨平台指令、图片渲染、WebUI 管理，基于 NoneBot2，即插即用。',
  head: [
    ['link', { rel: 'icon', href: '/icon.svg' }],
    // 社交平台抓取器对 SVG 支持差，补充 PNG 格式的 apple-touch-icon
    ['link', { rel: 'apple-touch-icon', href: '/images/studio/dashboard.png' }],
    // 告知搜索引擎站点主题色
    ['meta', { name: 'theme-color', content: '#1a1a1f' }],
  ],

  // 多语言支持（路径键需与主题 locales 保持一致）
  locales: {
    '/': {
      lang: 'zh-CN',
      title: 'Minecraft UniBot 文档',
      description: 'Minecraft UniBot 是开源免费的 Minecraft 群服互通机器人：支持 QQ、QQ 频道、Telegram、Discord、KOOK、DoDo 等聊天平台与多台 MC 服务器实时互通，跨平台指令、图片渲染、WebUI 管理，基于 NoneBot2，即插即用。',
    },
    '/en/': {
      lang: 'en-US',
      title: 'Minecraft UniBot Docs',
      description: 'Minecraft UniBot is a free, open-source cross-server bridge bot for Minecraft: connect QQ, Telegram, Discord, KOOK, DoDo and more chat platforms with multiple MC servers in real time. Cross-platform commands, image rendering and a WebUI, built on NoneBot2.',
    },
  },

  theme: plumeTheme({
    // 部署域名：用于 SEO（OGP / JSON-LD / canonical）与 sitemap.xml 的生成
    hostname: 'https://bot.mcjpg.dev/',

    logo: '/icon.svg',
    repo: 'MineJPGcraft/UniBot',
    docsDir: 'Docs/docs',

    markdown: {
      // 流程图（已从 flowchart 切换到 mermaid，节点内可用 <br/> 换行）：```mermaid
      mermaid: true,
      // 旧版 flowchart 语法（已弃用，保留配置以防残留代码块）：```flow:preset
      // flowchart: true,
      // Markdown 内联图标：::fluent-color:name::
      icon: { provider: 'iconify' },
      // 表格增强：::: table（标题 / 复制 / 高亮）
      table: true,
      // 折叠面板：::: collapse
      collapse: true,
      // 缩写词语法：*[xxx]: 定义
      abbr: true,
      // 隐秘文本
      plot: true,
      // 代码树：::: code-tree（文件树 + 代码块合并展示）
      codeTree: true,
    },

    social: [
      {
        icon: {
          svg: '<img src="https://mcjpg.org/logo.png" style="width:20px;height:20px;border-radius:50%;object-fit:cover;" />',
          name: 'mcjpg',
        },
        link: 'https://mcjpg.org/',
      },
      { icon: 'github', link: 'https://github.com/MineJPGcraft/UniBot' },
      { icon: 'qq', link: 'https://qm.qq.com/q/qyq2XH6qkw', ariaLabel: '加入 QQ 群' },
    ],

    navbarSocialInclude: ['github', 'mcjpg', 'qq'],

    // 主题级多语言配置（路径键与 VuePress locales 一致）
    locales: {
      '/': {
        selectLanguageName: '简体中文',

        navbar: [
          { text: '首页', link: '/' },
          { text: '指南', link: '/guide/' },
          { text: '核心', link: '/unibot/' },
          { text: '适配器', link: '/adapter/' },
          { text: '鸣谢', link: '/acknowledgements/' },
        ],

        sidebar: {
          '/guide/': [
            {
              text: '指南',
              collapsed: false,
              items: [
                '/guide/',
                '/guide/quick-start.md',
                '/guide/features.md',
                '/guide/command-reference.md',
                '/guide/webui.md',
                '/guide/image-rendering.md',
                '/guide/configuration.md',
              ],
            },
          ],
          '/unibot/': [
            {
              text: 'UniBot',
              collapsed: false,
              items: [
                '/unibot/',
                '/unibot/extension-system.md',
                '/unibot/architecture.md',
                '/unibot/api-reference.md',
                '/unibot/developing-extensions.md',
                '/unibot/marketplace.md',
              ],
            },
          ],
          '/adapter/': [
            {
              text: 'MC 适配器',
              collapsed: false,
              items: [
                '/adapter/',
                '/adapter/connect-chat-platforms.md',
                '/adapter/usage.md',
              ],
            },
          ],
          '/acknowledgements/': [
            {
              text: '鸣谢',
              collapsed: false,
              items: [
                '/acknowledgements/',
                '/acknowledgements/sponsors.md',
              ],
            },
          ],
        },
      },

      '/en/': {
        selectLanguageName: 'English',

        navbar: [
          { text: 'Home', link: '/en/' },
          { text: 'Guide', link: '/en/guide/' },
          { text: 'UniBot', link: '/en/unibot/' },
          { text: 'Adapters', link: '/en/adapter/' },
          { text: 'Acknowledgements', link: '/en/acknowledgements/' },
        ],

        sidebar: {
          '/guide/': [
            {
              text: 'Guide',
              collapsed: false,
              items: [
                '/en/guide/',
                '/en/guide/quick-start.md',
                '/en/guide/features.md',
                '/en/guide/command-reference.md',
                '/en/guide/webui.md',
                '/en/guide/image-rendering.md',
                '/en/guide/configuration.md',
              ],
            },
          ],
          '/unibot/': [
            {
              text: 'UniBot',
              collapsed: false,
              items: [
                '/en/unibot/',
                '/en/unibot/extension-system.md',
                '/en/unibot/architecture.md',
                '/en/unibot/api-reference.md',
                '/en/unibot/developing-extensions.md',
                '/en/unibot/marketplace.md',
              ],
            },
          ],
          '/adapter/': [
            {
              text: 'MC Adapter',
              collapsed: false,
              items: [
                '/en/adapter/',
                '/en/adapter/connect-chat-platforms.md',
                '/en/adapter/usage.md',
              ],
            },
          ],
          '/acknowledgements/': [
            {
              text: 'Acknowledgements',
              collapsed: false,
              items: [
                '/en/acknowledgements/',
                '/en/acknowledgements/sponsors.md',
              ],
            },
          ],
        },
      },
    },

    plugins: {
      // SEO：默认生成 OGP / JSON-LD / robots.txt，仅生产构建（vuepress build）生效
      seo: {
        // 站点默认作者（页面 frontmatter 中 author 优先）
        author: {
          name: 'McJPG 团队',
          url: 'https://mcjpg.org/',
        },
        // 无配图页面回退图：社交平台不支持 SVG，改用 PNG 截图
        fallBackImage: 'https://bot.mcjpg.dev/images/studio/dashboard.png',
        // canonical 链接基准地址（不配置则不会生成 canonical 标签）
        canonical: 'https://bot.mcjpg.dev/',
        // 补充默认 OGP：强制站点名；页面自身无图片时兜底 twitter 卡片
        ogp: (ogpInfo, page, app) => {
          const result = {
            ...ogpInfo,
            'og:site_name': 'Minecraft UniBot',
          }
          if (!ogpInfo['twitter:card']) {
            result['twitter:card'] = 'summary_large_image'
            result['twitter:image'] = ogpInfo['og:image']
            result['twitter:image:alt'] = ogpInfo['og:title']
          }
          return result
        },
      },
      // sitemap：生成 sitemap.xml（仅生产构建生效，hostname 自动继承顶层配置）
      sitemap: {},
      // GEO：生成 llms.txt / llms-full.txt 及每页 .md 纯文本版本，
      // 供 ChatGPT / Perplexity / Claude 等 AI 搜索引擎抓取（仅生产构建生效）
      llmstxt: {
        locale: 'all',
        // 生成绝对 URL，AI 智能体解析更可靠
        domain: 'https://bot.mcjpg.dev',
        // 自定义模板：备用语言链接移至末尾。
        // 插件会删除空占位符及其前面的空行（默认模板中 {alternateLinks} 紧跟 {details}，
        // 导致英文版无备用链接时 details 直接拼在 description 后）
        llmsTxtTemplate: '# {title}\n\n{description}\n\n{details}\n\n## Table of Contents\n\n{toc}\n\n{alternateLinks}',
        llmsTxtTemplateGetter: {
          // 主题内置 toc 仅支持「集合」结构，本站未使用集合，这里回退为插件的扁平目录：
          // - [标题](绝对 .md 链接): frontmatter 中的 description
          toc: (pages, { domain }) =>
            pages
              .map((page) => {
                const url = `${domain ?? ''}${page.path.replace(/\.html$/, '.md')}`
                const desc =
                  page.frontmatter.description && !page.data.autoDesc
                    ? `: ${page.frontmatter.description.trim()}`
                    : ''
                return `- [${page.title}](${url})${desc}\n`
              })
              .join(''),
        },
      },
    },
  }),

  bundler: viteBundler(),
})
