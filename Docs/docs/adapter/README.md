---
title: 适配器
description: UniBot 适配器总览：基于 NoneBot2 适配器接入 QQ、QQ 官方、Telegram、Discord、DoDo、KOOK、Satori 等聊天平台，以及通过鹊桥协议互通的 MC 适配器。
tags:
  - 适配器
  - 聊天平台
  - NoneBot2
---

# 适配器

适配器（Adapter）是 UniBot 与各聊天平台之间的桥梁，负责将机器人账号连接到对应平台，是机器人与外部平台对接的通道。

UniBot 基于 **NoneBot2** 框架，通过安装不同的 **NoneBot 适配器** 来接入不同平台。每个平台对应一个独立的适配器，在 `.env` 中配置各自的接入字段。

## 支持的平台

::: table title="支持的平台" copy="all" hl-cols="warning:4"
| 平台 | 适配器 | 说明 |
|------|--------|------|
| **QQ** | OneBot V11 | 需配合 Lagrange.OneBot / NapCat / LLOneBot 等协议端 |
| **QQ 官方** | QQ 官方机器人 | 通过 QQ 开放平台接入 |
| **Telegram** | Telegram | 官方 Bot API |
| **Discord** | Discord | 官方 Bot |
| **DoDo** | DoDo | 开放平台接入 |
| **KOOK（开黑啦）** | KOOK | 开发者平台接入 |
| **Satori** | Satori | 通用协议，可对接 Chronocat 等 |
| **Minecraft** | Minecraft | 通过鹊桥协议与服务器互通 |
:::

## 安装与依赖自动同步

通过 **WebUI → 适配器** 安装平台适配器时，UniBot 会自动完成三件事：

::: steps

1. **写入依赖**

   把适配器包（如 `nonebot-adapter-onebot`）写入 `pyproject.toml` 的 `dependencies`。

2. **追加驱动**

   在 `.env` 的 `DRIVER` 中追加适配器所需的驱动（如 `~httpx`、`~websockets`）。

3. **同步底层依赖**

   **自动把驱动所需底层依赖包**（如 `websockets`）同步写入 `pyproject.toml` 的 `dependencies`，确保重启后驱动可正常工作。

:::

以上依赖声明变化会在重启时由 Watchdog 通过 `uv sync` 自动落地安装。卸载适配器时，仅移除注册与 `DRIVER` 中多余的驱动，==不删除依赖声明==，避免误删被其他依赖引用的包。

## 快速导航

<LinkCard title="接入聊天平台" href="/adapter/connect-chat-platforms.html" icon="fluent-color:chat-24">

各平台适配器的配置字段与对接方式。

</LinkCard>

<LinkCard title="Minecraft 适配器" href="/adapter/usage.html" icon="fluent-color:link-24">

MC 协议适配器的配置、连接模式与服务器端接入。

</LinkCard>

## Minecraft 适配器

**NoneBot-Adapter-Minecraft** 是 NoneBot 的 Minecraft 协议适配器，为 UniBot 提供与 Minecraft 服务器通信的能力，是 UniBot 与服务器之间的桥梁。

它通过 **鹊桥** 协议，与服务器端的插件 / Mod 互通。

### 鹊桥协议

「鹊桥」是一套由 [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao) 开发的 **第三方通信协议**，负责打通 Minecraft 服务器与外部聊天系统（如 UniBot）。服务器端需安装 **鹊桥的实现端** 才能接入机器人，根据服务端类型不同，实现方式分为两类：

::: table title="接入方式" copy="all" hl-rows="tip:2"
| 服务端类型 | 实现端 | 说明 |
|------------|--------|------|
| MCDReforged（Java 版） | [MCDR 端插件](/adapter/usage.html#mcdr-端插件) | 运行于 MCDReforged 之上 |
| MCDReforged（基岩版 BDS） | [MCDR 端插件](/adapter/usage.html#基岩版-bedrock-支持) | 配合 Bedrock Liteloader Handler |
| Spigot / Paper / Folia / Forge / Fabric / NeoForge / Velocity / 原版 | [鹊桥官方实现](/adapter/usage.html#鹊桥官方实现) | 鹊桥官方实现 |
:::

鹊桥协议本身并非本项目开发，它还支持 Spigot、Paper、Fabric、Forge、NeoForge 等多种服务端。基岩版服务器可通过 MCDR 的 [Bedrock Liteloader Handler](https://mcdreforged.com/zh-CN/plugin/bedrock_liteloader_handler) 处理器接入，详见 [MCDR 端插件 · 基岩版支持](/adapter/usage.html#基岩版-bedrock-支持)。

### 协议概述

鹊桥 V2 协议基于 WebSocket，通过 `Authorization` 头鉴权，双向实时通信。服务端将游戏事件（玩家进出、聊天、死亡、成就等）转发给外部客户端，同时接收外部客户端发送的 API 指令（广播、私聊、Title、ActionBar、RCON 等）。

## 相关项目

::: table title="相关项目" copy="all"
| 项目 | 说明 |
|------|------|
| [MCDR 端插件](/adapter/usage.html#mcdr-端插件) | MCDReforged 端的鹊桥实现 |
| [鹊桥官方实现](/adapter/usage.html#鹊桥官方实现) | 其它服务端的鹊桥官方实现 |
| [nonebot-plugin-mcqq](https://github.com/17TheWord/nonebot-plugin-mcqq) | 更完善的 MC 通信插件 |
| [nonebot-plugin-mcping](https://github.com/17TheWord/nonebot-plugin-mcping) | 获取 MC 服务器 MOTD 并返回图片 |
:::

## 开源许可

本项目使用 [MIT](https://github.com/17TheWord/nonebot-adapter-minecraft) 许可证。