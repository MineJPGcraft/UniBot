---
title: "Configuration Guide"
date: 2026-08-21
description: "Minecraft UniBot configuration reference: the dual-file system of .env framework config and Config.toml business config, covering ports, commands, image rendering, WebUI and more."
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
| `Config/Messages.{zh,en}.toml` | `Config/` directory | User overrides of message text (only changed keys), hot-applies on save | TOML |
| `Core/Locales/System.{zh,en}.toml` | `Core/Locales/` directory | System built-in text (system commands + extension/plugin names + `api.*` UI text), read-only and not overridable | TOML |
| `Core/Locales/Messages.{zh,en}.toml` | `Core/Locales/` directory | Default translations of message text (shipped with the system) | TOML |
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

  # Whether to sync UniBot commands as group command panels for official QQ bots
  # When disabled, leftover panels are removed on bot connection
  sync_command_panels = true

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

## Language Packs & User Overrides

All of the bot's text is carried by a unified I18n engine with `{placeholder}` formatting. **Default translations and user overrides are kept separate**: language packs live under `Core/Locales/` (placed inside `Core/` to prevent accidental edits), while user changes are stored separately under `Config/`.

### Default translations (shipped with the system)

- **System layer `Core/Locales/System.{zh,en}.toml`** (shipped with the system, **read-only** and **not overridable**): contains the **system command** (`/bot`), the **names/descriptions of every extension/plugin**, and the **WebUI backend `api.*` interface text**.
- **Messages layer `Core/Locales/Messages.{zh,en}.toml`** (shipped with the system, used as the default translation): every message outside the system keys (event broadcasts, other commands, etc.).
- Extension packs live in `Extensions/<id>/Locales/{zh,en}.toml` under the `ext.<id>.*` namespace.

### User overrides (`Config/Messages.{zh,en}.toml`)

Changes made in the WebUI **Message Text** editor no longer rewrite the language packs; instead they are written to dedicated override files:

```
Config/Messages.zh.toml     # user overrides for Chinese messages
Config/Messages.en.toml     # user overrides for English messages
```

- Override files **store only the keys you changed**; unchanged keys are never written, and a key is removed automatically when it is reverted to the default translation.
- The effective priority is: **user override → default messages layer → system layer / extensions**. System-layer keys (system commands, extension/plugin names, `api.*` UI text) are **protected and cannot be overridden**.
- Overridability is decided by **file origin**: any key provided by `System.*.toml` is treated as a system key (protected); keys from `Messages.*.toml` or extension packs are user-overridable.
- Saving applies instantly with **no restart**. With `language = "zh"` the `zh` pack and its overrides are read; with `language = "en"` the `en` pack and its overrides are read.

```toml
# Config/Messages.zh.toml (contains only the keys you changed)
[core.events]
player_join = "玩家 {player} 上线啦！"

[core.commands.send]
sent = "已向服务器发送消息：{content}。"
```

::: tip Panel language and message language are independent
The WebUI panel language (Chinese / English) is switched from the top-right corner of the panel and stored only in your browser;
dynamic API messages follow the browser language automatically. Neither is related to the `language` field.
The **Message Text** editor edits overrides in the language that follows the **panel language** (a Chinese panel edits Chinese overrides, an English panel edits English overrides); no separate switch is needed.
:::

---

## Dependencies & Optional Features

Different optional features require additional dependencies, so sync the corresponding extra before enabling:

```bash
# WebUI admin panel
uv sync --no-dev --extra webui

# Extension dependencies (Python dependencies declared by enabled extensions)
uv sync --no-dev --extra webui --extra extensions
```

==Before enabling a feature, first confirm that the corresponding extra is installed==, otherwise the feature cannot work properly.

Image rendering's Python dependencies are declared by the **rendering engine extension itself** (`[dependencies].python` in `Extension.toml`) and synced via the `extensions` extra after installation — ==no separate image extra is needed==.

Dependency sync is handled by the in-process **Task Center**: trigger it manually from the Task Center in the top-right of the WebUI, or implicitly by installing/uninstalling an extension, plugin or adapter. All writes go through `uv add` / `uv remove` — never edit `pyproject.toml` by hand.
