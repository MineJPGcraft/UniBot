# Configuration

UniBot uses a **dual-config-file** system, separately managing the framework layer and the business layer configuration, each serving its own purpose.

## File Overview

::: table title="Configuration File Overview" copy="all"
| File | Location | Purpose | Format |
|------|------|------|------|
| `.env` | Project root | NoneBot framework config and adapter config | INI style |
| `Config.toml` | Project root | Bot custom config (commands, messages, images, etc.) | TOML |
| `Config/Extensions.toml` | `Config/` directory | Extension toggle switch (one key per extension) | TOML |
| `Config/Extensions/<id>.toml` | `Config/Extensions/` directory | Independent config for each extension (one file per extension) | TOML |
| `Config/Messages.toml` | `Config/` directory | Outbound message text (customizable) | TOML |
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

### Image Rendering Mode

::: collapse expand
- Example configuration

  ```toml
  [image]
  # Whether to enable image mode (requires the image dependency to be installed)
  mode = false

  # Background of the generated image (CSS background-image property)
  # Supports the random function, picking one at random from a local directory
  background = 'random("./Resources/Backgrounds/")'

  # Rendering engine to use (corresponds to an installed rendering engine extension; empty uses the default engine)
  # Takes effect after restart; automatically falls back to the default engine when unavailable
  renderer = ""

  # Template to use (corresponds to an installed template extension; empty uses the default template)
  # Takes effect immediately, no restart required
  template = ""
  ```
:::

---

## `Config/Extensions.toml` — Extension Toggle

This file records whether each extension is enabled, maintained automatically by the WebUI or the bot; it generally does not need manual editing.

```toml
[Default]
enabled = true

# The built-in rendering engine Html2Pic is gated by [image].mode and loads automatically when image mode is enabled
[Html2Pic]
enabled = true
```

---

## `Config/Extensions/` — Extension Configuration

Each extension that enables configuration corresponds to an independent config file `Config/Extensions/<extension ID>.toml`. When an extension declares config items in its manifest, the file is created automatically containing the default values of all config items; changes made in the WebUI or by the bot are written back automatically.

After modification, the extension validates and applies the config immediately; when validation fails, the original config is preserved unchanged.

---

## `Config/Messages.toml` — Message Text

All of the bot's outbound prompts/broadcast text is centralized in this file. It supports `{placeholder}` formatting and takes effect after restart.

```toml
[events]
player_join = "玩家 {player} 加入了游戏。"
player_join_group = "玩家 {player} 加入了 [{server}] 服务器，喵～"

[commands.send]
sent = "已向服务器发送消息：{content}。"

[commands.luck]
result = "你今天的人品为 {point}，{tips}"
```

*Note: do not delete existing keys.* Missing required items will cause the bot to fail to start.

---

## Dependencies & Optional Features

Different optional features require additional dependencies, so sync the corresponding extra before enabling:

```bash
# Image rendering mode
uv sync --extra image --inexact

# WebUI admin panel
uv sync --extra webui --inexact

# Extension dependencies (Python dependencies of installed extensions)
uv sync --extra extensions --inexact
```

==Before enabling a feature, first confirm that the corresponding extra is installed==, otherwise the feature cannot work properly.

*Watchdog automatically detects configuration changes and syncs the corresponding dependencies.*
