---
title: "MC Adapter"
date: 2026-08-21
description: "Usage of nonebot-adapter-minecraft: UniBot's built-in Minecraft protocol adapter, interconnecting with server-side plugins / Mods via the QueQiao protocol for group-server messaging."
---

# MC Adapter

`nonebot-adapter-minecraft` is NoneBot's Minecraft protocol adapter, used together with UniBot to interconnect with server-side plugins / Mods via the **QueQiao** protocol. The full documentation is available in its [Wiki](https://github.com/17TheWord/nonebot-adapter-minecraft/wiki).

## Installation

UniBot already includes this adapter as a built-in dependency, so no separate installation is needed. To use it standalone:

::: steps

1. **Install the adapter package**

   ```bash
   pip install nonebot-adapter-minecraft
   ```

2. **Register the adapter**

   Register it in `pyproject.toml`:

   ```toml
   [[tool.nonebot.adapters]]
   name = "Minecraft"
   module_name = "nonebot.adapters.minecraft"
   ```

:::

## Connection Modes

The adapter (i.e. the core of this project, running on the NoneBot server) communicates with the MC server side (MCDR plugin / official QueQiao implementation) over WebSocket. There are **two connection modes**, and you can choose either one:

- **Method 1: The MC server actively connects to the core** (Recommended)
- **Method 2: The core actively connects to the MC server**

Both modes require `server_name` and `access_token` to match on both ends, otherwise the connection will be rejected. See the [Connecting Modes](#connecting-modes) section for each plugin / Mod's connection configuration examples below.

### Method 1: MC Server Actively Connects to the Core (Recommended)

==This is the recommended mode.== That is, **the MC server actively connects to the core**: the QueQiao plugin / Mod on the MC server side acts as the connection initiator and actively connects to the WebSocket address exposed by the core (path `/minecraft/ws`).

**Advantages**

- Minecraft servers are often located behind intranets / NAT and cannot easily open inbound ports, while the server's outbound access to the public network / the core's address is usually unrestricted, so there is no need to open any port on the server.
- The core does not actively connect outward, so `MINECRAFT_WS_URLS` in `.env` can stay empty, making the configuration simpler.

**Disadvantages**

- The core's WebSocket address (`/minecraft/ws`) must be reachable by the MC server, meaning the core needs a public address or must be on the same intranet as the server.

### Method 2: Core Actively Connects to the MC Server

That is, **the core actively connects to the MC server**: the core acts as the connection initiator and actively connects to the WebSocket address exposed by the QueQiao plugin / Mod on the MC server side. In this case, what `MINECRAFT_WS_URLS` in `.env` holds is exactly **the WebSocket address of the MC server side**.

**Advantages**

- The core does not need to expose any port, suitable for scenarios where the core is on a strict intranet and cannot be reached by the MC server.

**Disadvantages**

- The MC server side needs to open a listening port to the outside, requiring the server to be able to expose ports (having a public address or being able to do port mapping).
- You need to manually fill in the address of each server in `MINECRAFT_WS_URLS` in `.env`, making the configuration relatively tedious.

## MC Server-Side Integration

The adapter communicates with the plugin / Mod on the MC server side through the QueQiao protocol. The MC server side can choose as follows:

- **MCDReforged**: use the [MCDR Plugin](#mcdr-plugin)
- **Other server types**: use the [Official QueQiao Implementation](#official-queqiao-implementation)

When integrating, ensure both ends match:

- **Server name**: `server_name` must match on both ends (under Method 2 "Core actively connects to the MC server", the key name in `MINECRAFT_WS_URLS` must match the MC server side's `server_name`).
- **Authentication token**: `MINECRAFT_ACCESS_TOKEN` must match the MC server side's `access_token` (verified when not empty).
- **Address reachability**: the WebSocket address and port must be reachable by both ends.

### Official QueQiao Implementation

The official QueQiao implementation applies to **Spigot / Paper / Folia / Forge / Fabric / NeoForge / Velocity / Vanilla** and other server types. The full documentation is available in the [Official QueQiao Docs](https://queqiao-docs.pages.dev).

#### Supported Server Types

::: table title="Supported Server Types" copy="all"
| Type | Description | Version Range |
|------|------|----------|
| Spigot / Paper / Folia | Bukkit-series plugin | From 1.12.2 |
| Forge / NeoForge | Mod loader | From 1.7.10 |
| Fabric | Mod loader | From 1.16.5 |
| Velocity | Proxy-side plugin | 3.3.0 |
| Vanilla | Standalone program (runs independently) | Vanilla |
:::

#### Installation

From [Modrinth](https://modrinth.com/plugin/queqiao) or [CurseForge](https://www.curseforge.com/minecraft/mc-mods/queqiao), download the plugin / Mod for **the corresponding server type**, place it in the server's corresponding directory, and start the server.

*The plugin version and the mod version have different config file paths.* The plugin version is at `./plugins/QueQiao/config.yml`, and the mod version is at `./config/QueQiao/config.yml`.

#### Configuration

The core `config.yml` configuration is as follows:

```yaml
enable: true # Whether to enable the plugin/mod

server_name: "Server" # Server name, use a different name for multiple servers
access_token: ""      # Verified on connection, no Bearer prefix needed; leave empty to skip verification

# Message prefix (not including Title, ActionBar), empty means no prefix is added
message_prefix: "[鹊桥]"

# Whether to enable message translation (converts translation keys such as achievements and deaths into localized text)
enable_translation: false

# WebSocket Server configuration (forward WebSocket)
websocket_server:
  enable: true          # Whether to enable
  host: "127.0.0.1"     # WebSocket Server address
  port: 8080            # WebSocket Server port

# WebSocket Client configuration (reverse WebSocket)
websocket_client:
  enable: false                 # Whether to enable
  reconnect_interval: 5         # Reconnect interval (seconds)
  reconnect_max_times: 5        # Maximum reconnect attempts
  url_list:
    - "ws://127.0.0.1:8080/minecraft/ws"

# Rcon client configuration
rcon:
  enable: false          # Whether to enable
  port: 25575            # Rcon port
  password: ""           # Rcon password

# Subscribed event configuration
subscribe_event:
  player_chat: true         # Player chat
  player_death: true        # Player death
  player_join: true         # Player join
  player_quit: true         # Player quit
  player_command: true      # Player command
  player_advancement: true  # Player advancement

# Ignored commands list; e.g. ["tp"] means command events starting with /tp are not broadcast
ignored_commands: []
```

##### Field Reference

::: table title="config.yml Field Reference" copy="all"
| Field | Description |
|------|------|
| `enable` | Whether to enable the plugin / mod |
| `server_name` | Server name, used for the Header `x-self-name` and event identification |
| `access_token` | Authentication token; leave empty to skip verification |
| `message_prefix` | Message prefix, supports MC text component JSON |
| `enable_translation` | Whether to enable the translation feature |
| `websocket_server` | Enable under Method 2 (core actively connects to the MC server), opens a listening port |
| `websocket_client` | Enable under Method 1 (MC server actively connects to the core), actively connects outward to the core |
| `rcon` | RCON client configuration |
| `subscribe_event` | Subscribed event toggles |
| `ignored_commands` | Ignored commands list |
:::

##### Translation Feature (Optional)

After enabling `enable_translation: true`, you also need to create a `translate` folder in the same directory as `config.yml` (plugin version at `./plugins/QueQiao/translate/`, mod version at `./config/QueQiao/translate/`), and place JSON language files there (such as `zh_cn.json` extracted from the client jar). This feature can convert translation keys in achievement and death events into localized text.

#### Connecting Modes

The official QueQiao implementation supports both modes described in [Connection Modes](#connection-modes) above; choose either one:

::: tabs
@tab Method 1: MC Server Actively Connects to the Core (Recommended)

Enable it in `websocket_client` and fill in the core's WebSocket address in `url_list`. The MC server actively connects outward to the core without opening any port. This suits scenarios where the server is on an intranet and cannot expose ports, ==and is the recommended choice in the vast majority of cases==.

**Core side (`.env`)**

```ini
# The core does not actively connect outward; keep it empty {} and do not fill in any address
MINECRAFT_WS_URLS={}

# Authentication token, keep consistent with the MC server side's access_token
# If the MC server side's access_token is empty, leave this empty too
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC server side (`config.yml`)**

```yaml
server_name: "survival"          # Server name, must match the key name in the core's MINECRAFT_WS_URLS
access_token: "your_access_token" # Authentication token, must match the core's MINECRAFT_ACCESS_TOKEN

# Reverse WebSocket: the MC server actively connects outward to the core
websocket_client:
  enable: true
  reconnect_interval: 5
  reconnect_max_times: 5
  url_list:
    - "ws://<core-ip>:8000/minecraft/ws"   # The core's WebSocket address

# Forward WebSocket: disabled in this mode
websocket_server:
  enable: false
```

*Here port `8000` is the bot core's listening port (`PORT` in `.env`, default `8000`), and the path is fixed at `/minecraft/ws`.*

@tab Method 2: Core Actively Connects to the MC Server

Enable it in `websocket_server` and listen on the address / port; the MC server opens a listening port and waits for the core to connect. This suits scenarios where the server can expose ports to the outside and the core connects actively.

**Core side (`.env`)**

```ini
# The key name is the server name, and the value is the MC server side's WebSocket address list
# The key name must match the MC server side's server_name
MINECRAFT_WS_URLS={"survival": ["ws://<mc-server-ip>:8080/mc"]}

# Authentication token, keep consistent with the MC server side's access_token
# If the MC server side's access_token is empty, leave this empty too
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC server side (`config.yml`)**

```yaml
server_name: "survival"          # Server name, must match the key name in the core's MINECRAFT_WS_URLS
access_token: "your_access_token" # Authentication token, must match the core's MINECRAFT_ACCESS_TOKEN

# Forward WebSocket: the MC server opens a listening port and waits for the core to connect
websocket_server:
  enable: true
  host: "0.0.0.0"
  port: 8080

# Reverse WebSocket: disabled in this mode
websocket_client:
  enable: false
```
:::

#### Header Authentication

When using either connection mode, the following Headers must be carried or verified:

::: table title="Header Authentication" copy="all"
| Header | Required | Description |
|--------|------|------|
| `x-self-name` | ::fluent-color:checkmark-circle-24:: | Server name, must match `server_name` in `config.yml` |
| `Authorization` | ::fluent-color:warning-24:: | Authentication, `Bearer <access_token>`; can be omitted when `access_token` is empty |
| `x-client-origin` | ::fluent-color:warning-24:: | Source marker of the integrating project, e.g. `minecraft` / `nonebot`; recommended to fill in |
:::

#### In-Game Commands

::: table title="In-Game Commands" copy="all"
| Command | Permission Node | Description |
|------|----------|------|
| `/queqiao help` | `queqiao.help` | Shows help |
| `/queqiao reload` | `queqiao.reload` | Reloads the config and restarts WebSocket |
| `/queqiao client reconnect [all]` | `queqiao.client.reconnect` | Reconnects the WebSocket Client (`all` forces reconnecting all) |
:::

*The mod side determines permissions by int Level; all commands in this mod have a permission of `2`.*

### MCDR Plugin

The **MCDR plugin** of QueQiao runs on top of MCDReforged and connects the Minecraft server to the QueQiao protocol. *This plugin only supports the MCDReforged server.* If you use other server types such as Spigot / Paper / Fabric / Forge / NeoForge, please refer to [Official QueQiao Implementation](#official-queqiao-implementation) above.

#### Features

- **Dual-mode WebSocket**: supports client mode (active connection) and server mode (passive listening).
- **Auto-reconnect**: client mode allows configuring the reconnect interval and the maximum retry count.
- **Hot reload**: `!!queqiao reload` reloads the config and reuses existing connections without restarting the server.
- **Game event forwarding**: player join / quit / chat / command / death / advancement.
- **API command execution**: broadcast, private message, Title, ActionBar, RCON commands, status query.

#### Installation

::: tabs
@tab Method 1: Download the .mcdr Package Directly

Download `queqiao-vX.X.X.mcdr` from [Releases](https://github.com/Minecraft-UniBot/QueQiao.MCDReforged/releases), place it in MCDR's `plugins/` directory, and restart MCDR.

@tab Method 2: Install from Source

```bash
git clone https://github.com/Minecraft-UniBot/QueQiao.MCDReforged.git
cd MCDReforged
uv sync
```

Place the entire directory as a Directory Plugin into the MCDR plugin directory, or package it yourself:

```bash
uv run python -m mcdreforged pack
```
:::

##### Dependencies

- **MCDReforged** ≥ 2.15.0
- **Python** ≥ 3.12
- Python packages: `websockets` ≥ 16.0, `PyYAML` ≥ 6.0, `psutil` ≥ 5.9
- MCDR plugin dependencies:

::: table title="MCDR Plugin Dependencies" copy="all"
| Plugin | Purpose | Required |
|------|------|------|
| [MoreGameEvents](https://mcdreforged.com/zh-CN/plugin/mg_events) | Player death and advancement events | ::fluent-color:checkmark-circle-24:: |
| [Minecraft Data API](https://mcdreforged.com/zh-CN/plugin/minecraft_data_api) | Player coordinates, health, experience level | ::fluent-color:checkmark-circle-24:: |
| [online_player_api](https://mcdreforged.com/zh-CN/plugin/online_player_api) | Online players list | ::fluent-color:warning-24:: Optional (falls back to MCDR built-in API when missing) |
:::

#### Configuration

On first load, a default configuration is generated at `config/queqiao/config.json`:

```json
{
  "server_name": "MCDR",
  "access_token": "",
  "client_origin": "mcdr",
  "minecraft": {
    "host": "",
    "port": 0
  },
  "client": {
    "enable": false,
    "url": "ws://127.0.0.1:8080/minecraft/ws",
    "reconnect_interval": 5,
    "reconnect_max_times": 0
  },
  "server": {
    "enable": false,
    "host": "0.0.0.0",
    "port": 8080
  },
  "log_events": true
}
```

##### Field Reference

::: table title="config.json Field Reference" copy="all"
| Field | Description |
|------|------|
| `server_name` | This server's name, used for Header `x-self-name` and event identification |
| `access_token` | Authentication token; when empty, the `Authorization` header is not sent |
| `client_origin` | Client origin identifier, default `mcdr` |
| `minecraft.host` / `minecraft.port` | MC server address, used for Server List Ping. Leave empty to resolve automatically from MCDR, falling back to `127.0.0.1:25565` if unresolved |
| `client.enable` | Set to `true` under Method 1 (MC server actively connects to the core) |
| `client.url` | The core's WebSocket address (filled in under Method 1) |
| `client.reconnect_interval` | Reconnect interval (seconds) |
| `client.reconnect_max_times` | Maximum reconnect attempts; `0` means retry indefinitely |
| `server.enable` | Set to `true` under Method 2 (core actively connects to the MC server) |
| `server.host` / `server.port` | WebSocket listening address (filled in under Method 2) |
| `log_events` | Whether to print event forwarding records in the log |
:::

#### Connecting Modes

The MCDR plugin supports both modes described in [Connection Modes](#connection-modes) above; choose either one:

::: tabs
@tab Method 1: MC Server Actively Connects to the Core (Recommended)

Set `client.enable` to `true` and fill in the core's WebSocket address (`client.url`). In this mode the MC server actively connects to the core and must keep `server_name` and `access_token` consistent with the core.

==This is the recommended mode.== When the server is on an intranet and cannot directly expose ports to the outside, the MC server can actively connect outward without opening any listening port on the server.

**Core side (`.env`)**

```ini
# The core does not actively connect outward; keep it empty {} and do not fill in any address
MINECRAFT_WS_URLS={}

# Authentication token, keep consistent with the MC server side's access_token
# If the MC server side's access_token is empty, leave this empty too
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC server side (`config.json`)**

```json
{
  "server_name": "survival",
  "access_token": "your_access_token",
  "client": {
    "enable": true,
    "url": "ws://<core-ip>:8000/minecraft/ws"
  },
  "server": {
    "enable": false
  }
}
```

*Here port `8000` is the bot core's listening port (`PORT` in `.env`, default `8000`), and the path is fixed at `/minecraft/ws`.*

@tab Method 2: Core Actively Connects to the MC Server

Set `server.enable` to `true`; the plugin will start a WebSocket server listening on `server.host:server.port`, waiting for the core to connect. You need to fill in the plugin's listening address in the core's `MINECRAFT_WS_URLS`.

**Core side (`.env`)**

```ini
# The key name is the server name, and the value is the MC server side's WebSocket address list
# The key name must match the MC server side's server_name
MINECRAFT_WS_URLS={"survival": ["ws://<mc-server-ip>:8080/mc"]}

# Authentication token, keep consistent with the MC server side's access_token
# If the MC server side's access_token is empty, leave this empty too
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC server side (`config.json`)**

```json
{
  "server_name": "survival",
  "access_token": "your_access_token",
  "server": {
    "enable": true,
    "host": "0.0.0.0",
    "port": 8080
  },
  "client": {
    "enable": false
  }
}
```
:::

#### Commands

::: table title="Command List" copy="all"
| Command | Permission | Description |
|------|------|------|
| `!!queqiao` | 2 | Shows help |
| `!!queqiao status` | 2 | Shows connection status (mode, players, CPU, memory, MOTD, etc.) |
| `!!queqiao reload` | 2 | Reloads the config and reconnects |
:::

#### Bedrock Support

This plugin runs on top of MCDReforged, and MCDR manages different types of Minecraft servers through **Server Handlers**. With the [Bedrock Liteloader Handler](https://mcdreforged.com/zh-CN/plugin/bedrock_liteloader_handler) handler, MCDR can directly host **Bedrock Dedicated Servers (BDS)**, allowing this plugin to also connect Bedrock servers to QueQiao.

##### How It Works

`bedrock_liteloader_handler` is an MCDR server handler that parses BDS's standard output into MCDR events (player join / quit, chat, etc.). Therefore, this plugin's event forwarding (player join/quit, chat) works **out of the box** on Bedrock servers, with no changes to the plugin code.

##### Installation and Configuration

::: steps

1. **Install the handler**: download the latest `.mcdr` package from [liteloader_handler Releases](https://github.com/Elec-Glacier/liteloader_handler/releases) and place it in MCDR's `plugins/` directory.

2. **Install this plugin**: install the QueQiao MCDR plugin per [Installation](#installation-2) above.

3. **Configure the handler**: after starting MCDR, a config file for the handler is generated under `config/`; select the corresponding Bedrock handler (the vanilla handler is used by default), then reload the config.

4. **Configure the QueQiao plugin**: fill in `config/queqiao/config.json` per [Configuration](#configuration-1) above, keeping `server_name` / `access_token` consistent with the adapter.

:::

##### Chat Output

The vanilla BDS **does not output player chat by default**. To have player chat events captured and forwarded by MCDR, you need to enable chat output through a **behavior pack** or by **modifying the server**; otherwise, player chat cannot be forwarded to QueQiao.

##### Known Limitations

Bedrock and Java are two different games, and some of this plugin's capabilities differ on Bedrock:

::: table title="Bedrock Capability Comparison" copy="all"
| Capability | Java Edition | Bedrock (BDS) |
|------|---------|---------------|
| Player join / quit events | ✅ | ✅ (parsed via handler) |
| Player chat events | ✅ | ✅ (requires behavior pack / modified server to enable output) |
| Player death / advancement events | ✅ (MoreGameEvents) | ::fluent-color:warning-24:: depends on Java events, usually not available |
| Player coordinates / health, etc. | ✅ (minecraft_data_api) | ❌ not available, field is `None` |
| Server List Ping (MOTD / online count) | ✅ (Java SLP protocol) | ❌ Bedrock uses the RakNet protocol, ping fails, `get_status` falls back |
| Broadcast / private message (`tellraw`) | ✅ | ::fluent-color:warning-24:: command syntax differs, needs adaptation |
| Title / ActionBar | ✅ | ::fluent-color:warning-24:: command syntax differs (e.g. `titleraw`) |
| RCON commands | ✅ | ::fluent-color:warning-24:: command set differs |
:::

*Because the command systems of Bedrock and Java differ greatly, if you need to use broadcast, private message, Title and other APIs on Bedrock, it is recommended to raise a request or submit an adaptation in the [QueQiao.MCDReforged](https://github.com/Minecraft-UniBot/QueQiao.MCDReforged) repository.*

##### Notes

- **LeviLamina**: After LeviLamina 1.0.0, MCDR cannot directly obtain the modified server output; you need an application supporting pty as a bridge (see [liteloader_handler#13](https://github.com/Elec-Glacier/liteloader_handler/issues/13)).
- **Unicode fix**: Affected by [BDS-3791](https://bugs.mojang.com/browse/BDS-3791), non-ASCII characters such as Chinese may display abnormally; you can install [UnicodeFixer](https://www.minebbs.com/resources/unicodefixer.6991/) to fix it.
- **Plugin compatibility**: Bedrock and Java are like two different games; before using other MCDR plugins, confirm whether they are compatible with Bedrock.

## Data Model

The adapter provides the following core types:

- `Bot`: bot instance
- `Message` / `MessageSegment`: message objects
- `Adapter`: adapter class
- Various event models (player events, chat events, etc.)

## Development and Debugging

You can run the adapter's test suite in the `tests/` directory:

```bash
uv run pytest
```

## Contribution and Support

- For usage issues, please submit [Issues](https://github.com/17TheWord/nonebot-adapter-minecraft/issues)
- Code contributions are welcome via [Pull requests](https://github.com/17TheWord/nonebot-adapter-minecraft/pulls)
