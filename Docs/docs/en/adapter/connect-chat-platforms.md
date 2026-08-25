---
title: "Connecting Chat Platforms"
date: 2026-08-21
description: "How to connect QQ, QQ Official, Telegram, Discord, DoDo and KOOK to UniBot: per-platform adapter fields in .env and filling bot cards in the WebUI."
---

# Connecting Chat Platforms

UniBot is built on NoneBot2 and connects to various chat platforms by installing different adapters. This page introduces the configuration fields and connection methods for each platform adapter. All configuration is done in the `.env` file in UniBot's root directory.

::: note Fill in bot cards directly in WebUI
If [WebUI](/en/guide/features.html) is enabled, ==you don't need to edit `.env` manually==: after logging in, go to **Config → Environment Variables**, and each platform's bot list fields (such as `QQ_BOTS`, `TELEGRAM_BOTS`, `DISCORD_BOTS`, etc.) are rendered as **bot cards**. Click **Add Item** to create a bot card and fill in fields such as `token`, `secret` one by one. Cards support expand / collapse, drag-to-sort, and deletion. After filling, save and restart the bot for the changes to take effect.
:::

*Note: list / object type configuration values should use JSON format and wrap the entire value in double quotes.* Configuration for adapters that are not installed will not be loaded.

## Common Framework Configuration

Before configuring the platforms, first confirm the following framework-level configuration:

```ini
# Listening port and host
PORT=8000
HOST="127.0.0.1"

# Superusers (admin accounts, can be multiple)
SUPERUSERS=["1234567890"]

# Command start character and separator
COMMAND_START=["#"]
COMMAND_SEP=[" "]

# Log level
LOG_LEVEL="INFO"

# Driver type (FastAPI)
DRIVER=~fastapi
```

*For public network access, change `HOST` to `0.0.0.0`.*

## QQ Official Bot (Recommended)

Connect via the QQ Open Platform. The bot list requires AppID / Token / Secret obtained after applying for an application on the Open Platform.

::: tip
If the version is ==higher than `v1.0.3`==, you can find a "scan to log in" button above the `Add Bot` card on the `WebUi` configuration page.
:::

```ini
QQ_BOTS=[]
QQ_IS_SANDBOX=false
```

::: table copy="all"
| Field | Description |
|------|------|
| `QQ_BOTS` | Bot configuration list (JSON array), each entry contains fields such as `id`, `token`, `secret`, `intent`, `use_websocket` |
| `QQ_IS_SANDBOX` | Whether to enable sandbox mode, default `false` |
:::

`QQ_BOTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `id` | Application AppID (obtained from the Open Platform) |
| `token` | Application Token |
| `secret` | Application Secret |
| `intent` | Event subscription (object type); optional fields include `guilds`, `guild_messages`, `at_messages`, etc. The default values are documented in the official docs |
| `use_websocket` | Whether to use a WebSocket connection, default `True`; when `False`, uses Webhook (requires public network) |
:::

## OneBot V11 (QQ)

OneBot V11 is the universal protocol for QQ, and must be used with a protocol client such as **[SnowLuma](https://snowluma.github.io/), NapCat, LLOneBot**.

```ini
# OneBot platform AccessToken, set by the OneBot server; leave empty if not enabled
ONEBOT_ACCESS_TOKEN=""
```

::: table copy="all"
| Field | Description |
|------|------|
| `ONEBOT_ACCESS_TOKEN` | Access token set by the OneBot server; leave empty if not enabled |
:::

*For multiple reverse connections, you can use fields such as `ONEBOT_WS_URLS`; see the OneBot adapter documentation for details.* When the protocol client acts as the server (reverse WebSocket), UniBot actively connects; see the [OneBot V11 adapter documentation](https://onebot.adapters.nonebot.dev/) for specific connection methods.

## Telegram

Connect via the official Bot API; the bot Token is obtained by applying to [@BotFather](https://t.me/BotFather).

```ini
TELEGRAM_BOTS=[]
TELEGRAM_WEBHOOK_URL=""
TELEGRAM_PROXY=""
```

::: table copy="all"
| Field | Description |
|------|------|
| `TELEGRAM_BOTS` | Bot configuration list (JSON array), each entry contains `token` and `is_webhook` fields |
| `TELEGRAM_WEBHOOK_URL` | Public HTTPS URL used in Webhook mode; leave empty in Long polling mode |
| `TELEGRAM_PROXY` | Proxy address for accessing the Telegram API, e.g. `http://127.0.0.1:10809`; the Socks protocol requires installing `httpx[socks]` |
:::

`TELEGRAM_BOTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `token` | Bot Token obtained from @BotFather (required) |
| `is_webhook` | Whether to enable Webhook mode, default `false` (i.e. Long polling mode by default) |
:::

## Discord

Connect via the official Bot; the bot Token is obtained after creating an application in the [Discord Developer Portal](https://discord.com/developers/applications).

```ini
DISCORD_BOTS=[]
DISCORD_API_VERSION=10
DISCORD_API_TIMEOUT=30
DISCORD_COMPRESS=false
DISCORD_HANDLE_SELF_MESSAGE=false
DISCORD_PROXY=""
```

::: table copy="all"
| Field | Description |
|------|------|
| `DISCORD_BOTS` | Bot configuration list (JSON array), each entry contains `token`, `intent`, `application_commands` fields |
| `DISCORD_API_VERSION` | Discord API version, default `10` |
| `DISCORD_API_TIMEOUT` | Discord API timeout (seconds), default `30` |
| `DISCORD_COMPRESS` | Whether to enable gateway data compression, default `false` |
| `DISCORD_HANDLE_SELF_MESSAGE` | Whether to handle messages sent by itself, default `false` |
| `DISCORD_PROXY` | Proxy address for accessing the Discord API; leave empty if not used |
:::

`DISCORD_BOTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `token` | Bot Token (required) |
| `intent` | Event subscription (object type); common fields: `guild_messages`, `direct_messages`, `message_content` (a privileged Intent, must be enabled in the Developer Portal) |
| `application_commands` | Slash command registration scope; `{"*": ["*"]}` registers everything as global commands, `{"command name": ["server ID"]}` registers as local commands for the specified server |
:::

## DoDo

Connect via the DoDo Open Platform; only WebSocket connections are supported.

```ini
DODO_BOTS=[]
```

::: table copy="all"
| Field | Description |
|------|------|
| `DODO_BOTS` | Bot configuration list (JSON array), each entry contains `client_id` and `token` fields |
:::

`DODO_BOTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `client_id` | Client ID obtained from the Open Platform (required) |
| `token` | Client token obtained from the Open Platform (required) |
:::

## KOOK (Kaiheila)

Connect via the KOOK Developer Platform; the bot Token is obtained from your application on the Developer Platform.

```ini
KAIHEILA_BOTS=[]
```

::: table copy="all"
| Field | Description |
|------|------|
| `KAIHEILA_BOTS` | Bot configuration list (JSON array), each entry contains a `token` field |
:::

`KAIHEILA_BOTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `token` | Token obtained from the Developer Platform - My Applications - Bot page (required) |
:::

## Satori

Satori is a universal protocol that can connect to platforms implementing the Satori protocol, such as Chronocat.

```ini
SATORI_CLIENTS=[]
```

::: table copy="all"
| Field | Description |
|------|------|
| `SATORI_CLIENTS` | Satori client list (JSON array), each entry contains `host`, `port`, `path`, `token`, `timeout`, `secure` fields |
:::

`SATORI_CLIENTS` fields per entry:

::: table copy="all"
| Field | Description |
|------|------|
| `host` | Satori server listening address, e.g. `localhost` (required) |
| `port` | Satori server listening port, e.g. `5500` (required) |
| `path` | Custom listening path for the Satori server, e.g. `/satori`; default empty string |
| `token` | Connection token; whether it is required is determined by the server (e.g. required when connecting to Chronocat) |
| `timeout` | Connection timeout (seconds), default `30` |
| `secure` | Whether to use a TLS-encrypted connection, default `false` |
:::

## Minecraft

Interconnects with Minecraft servers via the [QueQiao](/en/adapter/) protocol; see [Minecraft Adapter](/en/adapter/usage.html) for specific integration.

```ini
# Minecraft WebSocket addresses (supports multiple servers)
MINECRAFT_WS_URLS={"server1": ["ws://127.0.0.1:8080/mc"]}

# Server connection authentication token
MINECRAFT_ACCESS_TOKEN=""
```

::: table copy="all"
| Field | Description |
|------|------|
| `MINECRAFT_WS_URLS` | Server name → WebSocket address list (JSON object), supports multiple servers |
| `MINECRAFT_ACCESS_TOKEN` | Server connection authentication token, must match the server side |
:::

## Configuration Validation

After configuration is complete, restart the bot for the changes to take effect. If a platform's corresponding fields are not configured, that adapter will not be enabled. For the specific connection process and protocol client installation for each platform, please refer to the corresponding adapter's official documentation.
