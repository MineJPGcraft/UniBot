---
title: "Adapters"
description: "UniBot adapter overview: connect QQ, QQ Official, Telegram, Discord, DoDo, KOOK and Satori chat platforms via NoneBot2 adapters, plus the MC adapter using the QueQiao protocol."
tags:
  - adapters
  - chat platforms
  - NoneBot2
---

# Adapters

An Adapter is the bridge between UniBot and each chat platform, responsible for connecting the bot account to the corresponding platform. It is the channel through which the bot connects to external platforms.

UniBot is built on the **NoneBot2** framework and connects to different platforms by installing different **NoneBot adapters**. Each platform corresponds to an independent adapter, with its own connection fields configured in `.env`.

## Supported Platforms

::: table title="Supported Platforms" copy="all" hl-cols="warning:4"
| Platform | Adapter | Description |
|------|--------|------|
| **QQ** | OneBot V11 | Requires a protocol client such as Lagrange.OneBot / NapCat / LLOneBot |
| **QQ Official** | QQ Official Bot | Connect via the QQ Open Platform |
| **Telegram** | Telegram | Official Bot API |
| **Discord** | Discord | Official Bot |
| **DoDo** | DoDo | Open Platform connection |
| **KOOK (Kaiheila)** | KOOK | Developer Platform connection |
| **Satori** | Satori | Universal protocol, can connect to Chronocat, etc. |
| **Minecraft** | Minecraft | Interconnects with servers via the QueQiao protocol |
:::

## Installation and Automatic Dependency Sync

When installing a platform adapter through **WebUI → Adapters**, UniBot automatically does three things:

::: steps

1. **Write dependencies**

   Writes the adapter package (e.g. `nonebot-adapter-onebot`) into the `dependencies` of `pyproject.toml`.

2. **Append drivers**

   Appends the drivers required by the adapter (e.g. `~httpx`, `~websockets`) to `DRIVER` in `.env`.

3. **Sync underlying dependencies**

   **Automatically syncs the underlying dependency packages required by the driver** (e.g. `websockets`) into the `dependencies` of `pyproject.toml`, ensuring the driver works properly after a restart.

:::

The dependency changes above are applied automatically by the Watchdog via `uv sync` on restart. When uninstalling an adapter, only the registration and the redundant drivers in `DRIVER` are removed; ==dependency declarations are not deleted==, avoiding accidental removal of packages referenced by other dependencies.

## Quick Navigation

<LinkCard title="Connecting Chat Platforms" href="/en/adapter/connect-chat-platforms.html" icon="fluent-color:chat-24">

Configuration fields and connection methods for each platform adapter.

</LinkCard>

<LinkCard title="Minecraft Adapter" href="/en/adapter/usage.html" icon="fluent-color:link-24">

Configuration, connection modes, and server-side integration for the MC protocol adapter.

</LinkCard>

## Minecraft Adapter

**NoneBot-Adapter-Minecraft** is NoneBot's Minecraft protocol adapter, providing UniBot with the ability to communicate with Minecraft servers. It is the bridge between UniBot and servers.

It interconnects with the server-side plugin / Mod through the **QueQiao** protocol.

### QueQiao Protocol

"QueQiao" is a **third-party communication protocol** developed by [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao), responsible for bridging Minecraft servers with external chat systems (such as UniBot). The server side must install a **QueQiao implementation** to connect to the bot. Depending on the server type, the implementation falls into two categories:

::: table title="Connection Methods" copy="all" hl-rows="tip:2"
| Server Type | Implementation | Description |
|------------|--------|------|
| MCDReforged (Java Edition) | [MCDR Plugin](/en/adapter/usage.html#mcdr-plugin) | Runs on top of MCDReforged |
| MCDReforged (Bedrock BDS) | [MCDR Plugin](/en/adapter/usage.html#bedrock-support) | Works with the Bedrock Liteloader Handler |
| Spigot / Paper / Folia / Forge / Fabric / NeoForge / Velocity / Vanilla | [Official QueQiao Implementation](/en/adapter/usage.html#official-queqiao-implementation) | Official QueQiao implementation |
:::

The QueQiao protocol itself is not developed by this project; it also supports Spigot, Paper, Fabric, Forge, NeoForge and many other server types. Bedrock servers can connect through the MCDR [Bedrock Liteloader Handler](https://mcdreforged.com/zh-CN/plugin/bedrock_liteloader_handler) handler; see [MCDR Plugin · Bedrock Support](/en/adapter/usage.html#bedrock-support) for details.

### Protocol Overview

The QueQiao V2 protocol is based on WebSocket, authenticated via the `Authorization` header, with bidirectional real-time communication. The server forwards game events (player join/leave, chat, death, advancements, etc.) to the external client, and also receives API commands sent by the external client (broadcast, private message, Title, ActionBar, RCON, etc.).

## Related Projects

::: table title="Related Projects" copy="all"
| Project | Description |
|------|------|
| [MCDR Plugin](/en/adapter/usage.html#mcdr-plugin) | The QueQiao implementation for MCDReforged |
| [Official QueQiao Implementation](/en/adapter/usage.html#official-queqiao-implementation) | The official QueQiao implementation for other server types |
| [nonebot-plugin-mcqq](https://github.com/17TheWord/nonebot-plugin-mcqq) | A more complete MC communication plugin |
| [nonebot-plugin-mcping](https://github.com/17TheWord/nonebot-plugin-mcping) | Fetches the MC server MOTD and returns it as an image |
:::

## Open-Source License

This project is licensed under the [MIT](https://github.com/17TheWord/nonebot-adapter-minecraft) license.
