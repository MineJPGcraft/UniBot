---
title: "Configuration Guide"
date: 2026-08-21
description: "Minecraft UniBot configuration reference: the dual-file system of .env framework config and Config.toml business config, covering ports, commands, image rendering, WebUI and more."
tags:
  - configuration
  - .env
  - Config.toml
---

# Configuration Guide

UniBot uses a **dual-config-file** system, separately managing the framework layer and the business layer configuration, each serving its own purpose.

## File Overview

::: table title="Configuration File Overview" copy="all"
| File | Location | Purpose | Format |
|------|------|------|------|
| `.env` | Project root | NoneBot framework config and adapter config | INI style |
| `Config.toml` | Project root | Bot custom config (commands, messages, images, etc.) | TOML |
| `Config/Extensions.toml` | `Config/` directory | Extension toggle switch (one key per extension) | TOML |
| `Config/Extensions/<id>.toml` | `Config/Extensions/` directory | Independent config for each extension (one file per extension) | TOML |
| `Config/Messages.zh.toml` / `Config/Messages.en.toml` | `Config/` directory | Bilingual bot message packs (loaded by `language`) | TOML |
:::

==In daily use, the vast majority of configuration can be done visually in the WebUI without manually editing these files.== This page is for scenarios that require deep tuning or manual deployment.

---

## `.env` — Framework & Adapters

`.env` is used to configure the NoneBot framework itself, as well as the adapters for each platform.

### Framework Configuration

::: collapse expand
- Example configuration

  ```ini
  # Listen port and host
  PORT=8000
  HOST="127.0.0.1"

  # Superusers (admin accounts, can be multiple)
  SUPERUSERS=["1234567890"]

  # Command start character and separator
  COMMAND_START=["#"]
  COMMAND_SEP=[" "]

  # Log level
  LOG_LEVEL="INFO"
  ```
:::

### Minecraft Server Configuration

```ini
# Minecraft WebSocket addresses (multi-server supported)
# Format: {server name}: [{address list}]
MINECRAFT_WS_URLS={"server1": ["ws://127.0.0.1:8080/mc"]}

# Server access auth Token (must match the QueQiao plugin)
MINECRAFT_ACCESS_TOKEN=""
```

### Platform Adapter Configuration

Using OneBot V11 (QQ) as an example:

```ini
# OneBot connection method (forward / ws / reverse, etc.)
ONEBOT_ACCESS_TOKEN=""
ONEBOT_WS_URLS=["ws://127.0.0.1:6700"]
```

For other platforms (Telegram, Discord, Kook, etc.), refer to the corresponding adapter's documentation and configure the respective `BOT_TOKEN` and other fields in `.env`.

---

## `Config.toml` — Bot Configuration

`Config.toml` is the main configuration for the bot's business layer, using the TOML format. Nested tables are automatically flattened into config fields (for example, `enabled` under `[webui]` → `webui_enabled`).

### Basic Configuration

::: collapse expand
- Example configuration

  ```toml
  # Bot message language: zh / en, selects which Messages pack to load
  # Only affects messages sent by the bot; the WebUI panel language is switched separately inside the panel
  language = "zh"

  # Whether to treat all admins as superusers
  admin_superusers = true

  # Fake player prefix, the classification basis for the list command,
  # and the criterion for join-server broadcasts
  # Leave empty when there are no fake players or no classification needed
  bot_prefix = ""

  # Command groups: the bot only responds to commands in these groups
  # Format "{platform}:{group ID}"
  command_groups = ["qq_client:123456789"]

  # Message groups: groups that send messages into the game,
  # and synchronize game messages back to the group
  message_groups = ["qq_client:123456789"]

  # Whitelist / blacklist of commands that can be executed remotely via commands
  command_minecraft_whitelist = []
  command_minecraft_blacklist = ["kill"]
  ```
:::

::: note Faster authorization
`command_groups` / `message_groups` / `SUPERUSERS` can also be completed automatically through the **token authorization** guided by the WebUI "Quick Start": just send the auth token in any platform group chat. See [Feature Guide](/en/guide/features.html).
:::

### Message Sync

::: collapse expand
- Example configuration

  ```toml
  # Whether to broadcast server start/stop
  broadcast_server = true

  # Whether to broadcast player join/leave
  broadcast_player = true

  # Whether to forward all messages in message groups to the server in-game
  sync_all_qq_message = true

  # Whether to forward in-game server messages to QQ groups
  sync_all_game_message = false

  # Whether to forward in-game messages to other servers
  sync_message_between_servers = false

  # Sensitive word filter (not forwarded on hit, plus a violation reminder)
  sync_sensitive_words = ["敏感词", "你妈", "色图"]

  # Forwarded message colors (supports 16 MC colors or #hex)
  sync_color_source = "gray"
  sync_color_player = "gray"
  sync_color_message = "gray"

  # Maximum number of bound QQ accounts; 0 means no limit
  qq_bound_max_number = 1
  ```
:::

### Whitelist Configuration

```toml
# Whitelist command name
whitelist_command = "whitelist"

# Compatible mode for retrieving the player list (listens to join/leave updates; may be inaccurate)
list_compatible_mode = false
```

### WebUI Admin Panel

```toml
[webui]
# Whether to enable the WebUI (requires the webui dependency to be installed)
enabled = true
```

### Image Rendering

The `[image]` configuration, enabling steps, and appearance adjustments for image rendering are covered in [Image Rendering](/en/guide/image-rendering.html).

---

## `Config/Extensions.toml` — Extension Toggle

This file records whether each extension is enabled, maintained automatically by the WebUI or the bot; it generally does not need manual editing.

```toml
[Default]
enabled = true

# Rendering engine and default template extensions required by image mode (distributed via the official marketplace; auto-registered after installation)
[Html2Pic]
enabled = true
```

---

## `Config/Extensions/` — Extension Configuration

Each extension that enables configuration corresponds to an independent config file `Config/Extensions/<extension ID>.toml`. When an extension declares config items in its manifest, the file is created automatically containing the default values of all config items; changes made in the WebUI or by the bot are written back automatically.

After modification, the extension validates and applies the config immediately; when validation fails, the original config is preserved unchanged.

---

## `Config/Messages.zh.toml` / `Config/Messages.en.toml` — Message Text

All of the bot's outbound prompts/broadcast text is centralized in message pack files. They support `{placeholder}` formatting and apply instantly after saving in the WebUI.

- With `language = "zh"`, `Messages.zh.toml` is loaded (the legacy single file `Messages.toml` is still accepted as a Chinese-pack fallback)
- With `language = "en"`, `Messages.en.toml` is loaded
- Both packs share identical keys and can be customized independently; switch packs via the `language` field in `Config.toml`

```toml
[events]
player_join = "玩家 {player} 加入了游戏。"        # en pack: "Player {player} joined the game."

[commands.send]
sent = "已向服务器发送消息：{content}。"

[commands.luck]
result = "你今天的人品为 {point}，{tips}"
```

*Note: do not delete existing keys.* Missing required items will cause the bot to fail to start.

::: tip Hidden blocks (# Hidden Start / # Hidden End)
The `# Hidden Start` / `# Hidden End` comment lines and everything between them are **completely hidden** from the WebUI message editor:
on save they are re-inserted at their original position (located by the visible content preceding each block) and are still loaded by the bot.
If the locating content is deleted, the block is appended to the end of the file with full markers on save — data is never lost.
Do not type these markers manually in the WebUI editor (they are ignored).
:::

::: tip Panel language and message language are independent
The WebUI panel language (Chinese / English) is switched from the top-right corner of the panel and stored only in your browser;
dynamic API messages follow the browser language automatically. Neither is related to the `language` field.
:::

---

## Dependencies & Optional Features

Different optional features require additional dependencies, so sync the corresponding extra before enabling:

```bash
# WebUI admin panel
uv sync --extra webui --inexact

# Extension dependencies (Python dependencies declared by enabled extensions)
uv sync --extra extensions --inexact
```

==Before enabling a feature, first confirm that the corresponding extra is installed==, otherwise the feature cannot work properly.

Image rendering's Python dependencies are declared by the **rendering engine extension itself** (`[dependencies].python` in `Extension.toml`) and synced via the `extensions` extra after installation — ==no separate image extra is needed==.

*Watchdog automatically detects configuration changes and syncs the corresponding dependencies.*
