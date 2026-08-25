---
title: 功能特性
date: 2026-08-04
description: UniBot 功能特性一览：QQ 与 Minecraft 群服互通、跨服聊天、跨平台指令、图片渲染卡片、WebUI 可视化管理、白名单管理、扩展系统与扩展市场。
---

# 功能特性

UniBot 提供丰富的功能，覆盖群服互通、图片渲染、WebUI 管理等多个方面。

## 群服互通

UniBot 的核心能力，是让 Minecraft 与聊天平台 *实时互通*：

- ::fluent-color:checkmark-circle-24:: 游戏内实时看到 QQ 群消息
- ::fluent-color:checkmark-circle-24:: QQ 群内看到游戏内聊天，支持文字、图片等消息类型
- ::fluent-color:checkmark-circle-24:: 玩家 **加入 / 离开 / 死亡** 全事件播报
- ::fluent-color:checkmark-circle-24:: 服务器 **开启 / 关闭** 自动通知
- ::fluent-color:checkmark-circle-24:: 多服消息互转，构建分布式 MC 网络

### 消息同步方向

::: table title="消息同步方向" copy="all"
| 方向 | 配置项 | 说明 |
|------|--------|------|
| 群 → 服务器 | `sync_all_qq_message` | 群内消息自动转发到游戏 |
| 服务器 → 群 | `sync_all_game_message` | 游戏内消息自动转发到群 |
| 服务器 → 服务器 | `sync_message_between_servers` | 多服消息互转 |
:::

### 事件播报

已接入的播报事件：

- 玩家加入 / 离开
- 玩家死亡
- 玩家成就
- 服务器开启 / 关闭

*玩家死亡与成就事件需在 MCDR 端安装 [MoreGameEvents](https://mcdreforged.com/zh-CN/plugin/mg_events) 插件。*

### 敏感词过滤

通过 `sync_sensitive_words` 配置，命中敏感词的消息不会转发到群，而是提醒违禁。

---

## 图片渲染

图片渲染让机器人的指令输出以 **图片** 形式发送，支持列表、运势、状态等指令，能力由**渲染引擎、模板、资源**三类扩展协作提供。

图片渲染功能较为独立，完整的启用步骤、配置与外观调整见 [图片渲染](/guide/image-rendering.html)。

---

## WebUI 管理面板

UniBot 内置了基于 **Vue 3 + Vite** 构建的 Web 管理面板，通过 REST API 与后端交互。提供仪表盘实时监控、服务器 / 玩家管理、可视化配置、扩展管理、日志查看等能力，**使用 WebUI 后基本无需手动修改配置文件**。

- **仪表盘**：实时运行状态 + 「快速开始」引导卡片
- **可视化配置**：`Config.toml` / `.env` / `Messages.toml` 分组编辑，Schema 校验
- **服务器 / 玩家 / 适配器 / 插件 / 扩展**：一站式管理
- **日志查看**：WebSocket 实时滚动 + 级别筛选
- **登录认证**：JWT + HttpOnly Cookie，管理员账户体系

::: note
各页面功能详解、启用方式、初始化管理员与常见问题，见 **[WebUI 管理面板](/guide/webui.html)**。
:::

---

## 扩展系统

UniBot 基于 **NoneBot2** 构建，可无缝接入 [NB 插件商店](https://registry.nonebot.dev/)，社区现成插件开箱即用；内置的扩展机制则让机器人能力可以像积木一样自由组合：

- **五类扩展**：指令、服务、渲染引擎、模板、资源，按需安装、按需启停。
- **开箱即用**：内置指令与模板均已预置，无需额外配置。
- **稳定可靠**：单个扩展异常不会拖垮整个机器人，失效扩展会被自动隔离并标注原因。
- **依赖感知**：扩展间的依赖关系自动解析，缺失或版本不兼容时会明确提示。
- **可视化管理**：WebUI 中即可完成扩展的启停、配置与渲染引擎 / 模板切换。
- **AI 零代码开发**：不会写代码也能做扩展 —— WebUI 扩展页右上角「创意工坊」一键启动 **AiStudio**，用自然语言描述需求即可自动生成、校验并安装扩展。

更详细的说明见 [扩展系统](/unibot/extension-system.html)。

---

## 白名单管理

完善的平台账号与游戏 ID 绑定系统：

- 支持多服白名单同步。
- 绑定数量可配置（`qq_bound_max_number`）。
- 通过 `/bound` 指令即可管理。

---

## 对比同类方案

::: table title="对比同类方案" copy="all" hl-cols="success:2"
| 特性 | **UniBot** | 传统方案 |
|------|-----------|---------|
| 多平台支持 | ::fluent-color:checkmark-circle-24:: QQ / Telegram / Discord / Kook… | ::fluent-color:dismiss-circle-24:: 通常仅 QQ |
| 多服互联 | ::fluent-color:checkmark-circle-24:: 原生支持，消息互转 | ::fluent-color:dismiss-circle-24:: 需自行改装 |
| WebSocket 通信 | ::fluent-color:checkmark-circle-24:: 实时长连接 | ::fluent-color:warning-24:: 多为 HTTP 轮询 |
| 扩展系统 | ::fluent-color:checkmark-circle-24:: 指令 / 服务 / 渲染 / 模板 / 资源，即插即用 | ::fluent-color:dismiss-circle-24:: 单体耦合 |
| NoneBot2 生态 | ::fluent-color:checkmark-circle-24:: 无缝接入 NB 插件商店 | ::fluent-color:dismiss-circle-24:: 闭源自研 |
| WebUI | ::fluent-color:checkmark-circle-24:: Vue 3 管理面板 | ::fluent-color:dismiss-circle-24:: 无 |
| 图片渲染 | ::fluent-color:checkmark-circle-24:: HTML/CSS 模板引擎 | ::fluent-color:dismiss-circle-24:: 无 |
| 白名单管理 | ::fluent-color:checkmark-circle-24:: 完善的绑定系统 | ::fluent-color:dismiss-circle-24:: 无或基础 |
:::