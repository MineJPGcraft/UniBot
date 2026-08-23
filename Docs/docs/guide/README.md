# 指南

欢迎使用 **Minecraft UniBot**。本指南作为**用户手册**，帮助你安装机器人并快速上手使用。如需深入调整配置，请跳转到 [配置指南](/guide/configuration.html)。

==首次使用请从「快速开始」开始==，按步骤完成部署即可；其余页面按需查阅。

## 从哪开始

:::: card-grid

::: card title="快速开始" icon="fluent-color:book-open-24"
第一次接触？从这里开始，按步骤完成最小部署。

→ [前往快速开始](/guide/quick-start.html)
:::

::: card title="指令手册" icon="fluent-color:book-24"
全部内置指令及用法，一查便知。

→ [前往指令手册](/guide/command-reference.html)
:::

::: card title="功能特性" icon="fluent-color:bot-sparkle-24"
群服互通、图片渲染、WebUI、扩展系统等全部能力。

→ [查看功能特性](/guide/features.html)
:::

::: card title="WebUI 管理面板" icon="fluent-color:board-24"
可视化配置、实时监控、服务器 / 玩家管理、日志查看。

→ [了解 WebUI](/guide/webui.html)
:::

::: card title="配置指南" icon="fluent-color:settings-24"
需要深入调整配置？`.env` 与 `Config.toml` 全部配置项尽在其中。

→ [查看配置指南](/guide/configuration.html)
:::

::: card title="架构设计" icon="fluent-color:apps-24"
了解整体架构及各组件间的通信方式。

→ [查看架构设计](/unibot/architecture.html)
:::

::: card title="扩展系统" icon="fluent-color:puzzle-piece-24"
了解扩展机制，像积木一样组合机器人能力。

→ [查看扩展系统](/unibot/extension-system.html)
:::

::::

## 文档导航

::: table title="文档导航" copy="all"
| 章节 | 内容 | 适合谁 |
|------|------|--------|
| [快速开始](/guide/quick-start.html) | 五步完成部署 | 第一次使用的用户 |
| [指令手册](/guide/command-reference.html) | 全部内置指令及用法 | 所有用户 |
| [功能特性](/guide/features.html) | 群服互通、图片渲染、WebUI、扩展系统等能力 | 想了解全部能力的用户 |
| [WebUI 管理面板](/guide/webui.html) | WebUI 各页面功能、启用方式与常见问题 | 使用 WebUI 的用户 |
| [配置指南](/guide/configuration.html) | `.env`、`Config.toml` 等全部配置项的详细说明 | 需要深入调整配置的用户 |
:::

> ::fluent-color:link-24:: **配置指南**：`.env` 与 `Config.toml` 等全部配置项的详细说明，见 [配置指南](/guide/configuration.html)。

## 项目组成

本项目由多个子项目组成，各负责一个环节：

::: table title="项目组成" copy="all"
| 子项目 | 作用 | 文档 |
|--------|------|------|
| [UniBot](/unibot/) | 核心机器人，负责与聊天平台、多台服务器通信 | [架构设计](/unibot/architecture.html) |
| [MC 适配器](/adapter/) | NoneBot 的 MC 协议适配器，通信桥梁 | [适配器文档](/adapter/) |
:::

> ::fluent-color:pin-24:: **关于鹊桥**：鹊桥是一套第三方通信协议，由 [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao) 官方维护，支持 MCDReforged、Spigot、Paper、Fabric、Forge 等多种服务端。UniBot 通过 [MC 适配器](/adapter/) 与鹊桥互通。