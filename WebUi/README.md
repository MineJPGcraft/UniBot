# Minecraft UniBot WebUI

> 🖥️ UniBot 的现代化 Web 管理面板前端 — 基于 **Vue 3 + Vite + Pinia + reka-ui** 构建。
>
> 提供了可视化配置、实时监控、服务器/玩家管理、日志查看等能力，通过与 UniBot 后端的 REST API 与 WebSocket 交互。

## ✨ 功能

| 视图 | 功能 |
|------|------|
| 📊 仪表盘 | 实时查看机器人运行状态、内存占用、在线服务器数、已绑定玩家数 |
| 📋 服务器管理 | 查看各服务器连接状态、在线玩家、详情，远程执行指令 |
| 👥 玩家管理 | 管理白名单绑定关系，查看所有已绑定玩家 |
| 🛰️ 适配器管理 | 查看已安装的平台通信适配器（Minecraft / OneBot V11 等） |
| 🧩 插件管理 | 查看已加载插件列表及其启停状态 |
| ⚙️ 配置管理 | 可视化编辑 `Config.toml` 与 `.env`，Schema 校验、分组展示 |
| 🙋 用户管理 | 管理系统登录账户、角色与权限 |
| 📄 日志查看 | 通过 WebSocket 实时滚动查看运行日志，支持分级筛选 |
| 🔐 登录认证 | JWT + 密码认证（HttpOnly Cookie），首次访问引导初始化管理员账户 |

## 📦 构建产物

本目录是 **UniBot 核心仓库的一部分**（`UniBot/WebUi/`），存放前端源码。发布时通过
`vite build` 构建出静态资源（`index.html` + `assets/`），由 `release.yml` 打包进
`UniBot.zip`。

产物有两种布局，后端 `webui_manager` 会自动识别（WebUI 为内置功能，无需开关）：

```txt
[bun run build]  ──►  WebUi/dist/           # 本地构建布局（不入库）
                          ├── index.html
                          └── assets/       # JS / CSS 静态资源
        │
        │  CI 打包时把 dist/ 的内容直放 WebUi/ 下
        ▼
发布包布局：WebUi/index.html + WebUi/assets/   # 不套一层 dist/
        │
        ▼
UniBot 启动时托管  ──►  访问 /webui
```

> 一般用户无需手动构建：发布包已内置产物。

## 📁 项目结构

```
WebUi/
├── index.html               # HTML 入口
├── vite.config.js           # Vite 配置（base=/webui/，dev 代理 API）
├── jsconfig.json            # VSCode 路径别名（@ → src）
├── package.json
└── src/
    ├── main.js              # Vue 应用入口
    ├── App.vue              # 根组件
    ├── router/              # 路由配置（含登录守卫）
    ├── stores/              # Pinia 状态
    │   ├── auth.js          # 认证：登录 / 初始化 / 用户
    │   ├── adapter.js       # 适配器
    │   ├── config.js        # 配置管理
    │   ├── plugin.js        # 插件
    │   ├── player.js        # 玩家
    │   ├── server.js        # 服务器
    │   ├── status.js        # 状态
    │   └── user.js          # 用户
    ├── utils/
    │   ├── http.js          # fetch 封装（JWT 刷新 / 统一响应解析）
    │   ├── format.js        # 格式化工具
    │   └── server.js        # 服务器工具
    ├── composables/         # Vue 组合式函数
    ├── components/          # 通用组件
    ├── views/               # 页面视图
    └── styles/              # 全局样式
```

## 🚀 本地开发

前置要求：**Node.js** `^22.18.0 || >=24.12.0`，推荐使用 [bun](https://bun.sh/)。

```bash
# 安装依赖
bun install

# 启动开发服务器（热更新）
bun run dev
```

开发时用 **dev 模式**启动后端，避免后端托管本地产物、干扰热更新：

```bash
# 在 UniBot/ 目录
UNIBOT_DEV=1 uv run Watchdog.py
```

dev 模式下后端只挂载 `/webui/api`，**不托管**前端产物，也不注册前端页面路由
（访问后端端口的前端页面只会 404），启动日志会提示当前处于 dev 模式。
界面请访问 Vite dev server：`http://localhost:5173/webui/`。

`vite.config.js` 已将 `/webui/api` 代理到 `http://localhost:8000`，因此开发时可让后端在
`8000` 端口运行，前后端联调无需额外配置。

> ⚠️ 注意：`/webui/ws` 不做代理，开发环境下 WebSocket 由前端直连后端（避免 Bun 下 http-proxy 兼容问题）。

## 🔨 生产构建

```bash
bun run build
```

产物输出到 `dist/`，由 UniBot 后端直接托管（本地构建布局）；发布包会把 `dist/` 的内容
直放 `WebUi/` 后再打包进 `UniBot.zip`。

## 🧪 接口约定

- **基础路径**：`/webui/api`
- 认证通过 **HttpOnly Cookie**（`unibot_access_token` / `unibot_refresh_token`）自动携带，前端 JS 无法读取；`access_token` 过期时 `http.js` 会自动用刷新令牌重试。
- 所有请求 `credentials: 'include'`。
- 响应统一格式：`{ "code": 0, "data": ..., "message": "ok" }`，`code !== 0` 时抛出 `ApiError`。

详细 API 文档见仓库根目录 [`webui.md`](../webui.md)。

## 🧰 技术栈

- [Vue 3](https://vuejs.org/) + `<script setup>` 组合式 API
- [Vite](https://vitejs.dev/) — 构建工具
- [Pinia](https://pinia.vuejs.org/) — 状态管理
- [Vue Router](https://router.vuejs.org/) — 路由（`createWebHistory`）
- [reka-ui](https://reka-ui.com/) — 无头 UI 组件库（Dialog、Select、Toast 等）
- [Codemirror](https://codemirror.net/) — TOML 配置代码编辑器
- [oxfmt](https://github.com/oxc-project/oxc/tree/main/npm/oxfmt) — 代码格式化（`bun run format`）

## 📄 License

本项目随 UniBot 采用 [GPL-3.0](../UniBot/LICENSE) 许可证。修改后需开源并注明出处，禁止商用。
