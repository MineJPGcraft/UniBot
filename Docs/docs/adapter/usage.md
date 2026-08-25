---
title: MC 适配器
date: 2026-08-04
description: nonebot-adapter-minecraft MC 适配器使用说明：UniBot 内置的 Minecraft 协议适配器，通过鹊桥协议与服务器端插件 / Mod 互通，实现群服消息同步。
---

# MC 适配器

`nonebot-adapter-minecraft` 是 NoneBot 的 Minecraft 协议适配器，随 UniBot 一起使用，负责通过 **鹊桥** 协议与服务器端的插件 / Mod 互通。完整文档可参阅其 [Wiki](https://github.com/17TheWord/nonebot-adapter-minecraft/wiki)。

## 安装

UniBot 已内置该适配器作为依赖，无需单独安装。若需单独使用：

::: steps

1. **安装适配器包**

   ```bash
   pip install nonebot-adapter-minecraft
   ```

2. **注册适配器**

   在 `pyproject.toml` 中注册：

   ```toml
   [[tool.nonebot.adapters]]
   name = "Minecraft"
   module_name = "nonebot.adapters.minecraft"
   ```

:::

## 连接模式

适配器（即本项目核心，运行于 NoneBot 服务器）与 MC 服务器端（MCDR 插件 / 鹊桥官方实现）通过 WebSocket 通信，共有 **两种连接方式**，任选其一即可：

- **方式一：MC 服务器主动连接核心**（推荐）
- **方式二：核心主动连接 MC 服务器**

两种方式均要求两端 `server_name` 与 `access_token` 一致，否则连接会被拒绝。具体配置示例见下文各插件 / Mod 的 [连接模式对接](#连接模式对接)。

### 方式一：MC 服务器主动连接核心（推荐）

==推荐使用这种方式。== 即 **MC 服务器主动去连接核心**：MC 服务器端的鹊桥插件 / Mod 作为连接发起方，主动连接核心暴露的 WebSocket 地址（路径 `/minecraft/ws`）。

**优点**

- Minecraft 服务器常位于内网 / NAT 之后，难以对外开放入站端口，而服务器主动访问公网 / 核心所在地址通常不受限制，因此无需在服务器上开放任何端口。
- 核心不主动外连，`.env` 中的 `MINECRAFT_WS_URLS` 保持为空即可，配置更简单。

**缺点**

- 需要核心的 WebSocket 地址（`/minecraft/ws`）能被 MC 服务器访问到，即核心需有公网地址或与服务器在同一内网。

### 方式二：核心主动连接 MC 服务器

即 **核心主动去连接 MC 服务器**：核心作为连接发起方，主动连接 MC 服务器端鹊桥插件 / Mod 暴露的 WebSocket 地址。此时 `.env` 中的 `MINECRAFT_WS_URLS` 填写的正是 **MC 服务器端 WebSocket 的地址**。

**优点**

- 核心无需对外暴露端口，适用于核心处于严格内网、无法被 MC 服务器访问的场景。

**缺点**

- MC 服务器端需要对外开放监听端口，要求服务器能暴露端口（有公网地址或可做端口映射）。
- 需要在 `.env` 的 `MINECRAFT_WS_URLS` 中手动填写每个服务器的地址，配置相对繁琐。

## MC 服务器端接入

适配器通过鹊桥协议与 MC 服务器端的插件/Mod 通信。MC 服务器端可作如下选择：

- **MCDReforged**：使用 [MCDR 端插件](#mcdr-端插件)
- **其他服务端**：使用 [鹊桥官方实现](#鹊桥官方实现)

对接时需保证两端一致：

- **服务器名称**：两端 `server_name` 一致（方式二「核心主动连接 MC 服务器」下，`MINECRAFT_WS_URLS` 键名须与 MC 服务器端 `server_name` 一致）。
- **鉴权 Token**：`MINECRAFT_ACCESS_TOKEN` 与 MC 服务器端 `access_token` 一致（不为空时校验）。
- **地址可达**：WebSocket 地址与端口互通。

### 鹊桥官方实现

鹊桥官方实现适用于 **Spigot / Paper / Folia / Forge / Fabric / NeoForge / Velocity / 原版** 等其它服务端。完整文档请参阅 [鹊桥官方文档](https://queqiao-docs.pages.dev)。

#### 支持的服务端

::: table title="支持的服务端" copy="all"
| 类型 | 说明 | 版本范围 |
|------|------|----------|
| Spigot / Paper / Folia | Bukkit 系插件 | 1.12.2 起 |
| Forge / NeoForge | Mod 加载器 | 1.7.10 起 |
| Fabric | Mod 加载器 | 1.16.5 起 |
| Velocity | 代理端插件 | 3.3.0 |
| 原版 | 独立程序（独立运行） | 原版 |
:::

#### 安装

从 [Modrinth](https://modrinth.com/plugin/queqiao) 或 [CurseForge](https://www.curseforge.com/minecraft/mc-mods/queqiao) 下载 **对应服务端类型** 的插件 / Mod，放入服务端对应目录后启动即可。

*插件端与模组端的配置文件路径不同。* 插件端位于 `./plugins/QueQiao/config.yml`，模组端位于 `./config/QueQiao/config.yml`。

#### 配置

`config.yml` 核心配置如下：

```yaml
enable: true # 是否启用插件/模组

server_name: "Server" # 服务器名称，多个服务器时使用不同命名
access_token: ""      # 连接时验证用，无需 Bearer 前缀，留空则不验证

# 消息前缀（不含 Title、ActionBar），为空则不添加
message_prefix: "[鹊桥]"

# 是否启用消息翻译（成就、死亡等翻译键转本地化文本）
enable_translation: false

# WebSocket Server 配置项（正向 WebSocket）
websocket_server:
  enable: true          # 是否启用
  host: "127.0.0.1"     # WebSocket Server 地址
  port: 8080            # WebSocket Server 端口

# WebSocket Client 配置项（反向 WebSocket）
websocket_client:
  enable: false                 # 是否启用
  reconnect_interval: 5         # 重连间隔（秒）
  reconnect_max_times: 5        # 最大重连次数
  url_list:
    - "ws://127.0.0.1:8080/minecraft/ws"

# Rcon 客户端配置项
rcon:
  enable: false          # 是否启用
  port: 25575            # Rcon 端口
  password: ""           # Rcon 密码

# 订阅事件配置项
subscribe_event:
  player_chat: true         # 玩家聊天
  player_death: true        # 玩家死亡
  player_join: true         # 玩家加入
  player_quit: true         # 玩家退出
  player_command: true      # 玩家命令
  player_advancement: true  # 玩家成就

# 忽略的命令列表，如 ["tp"] 则所有以 /tp 起始的命令事件不被广播
ignored_commands: []
```

##### 字段说明

::: table title="config.yml 字段说明" copy="all"
| 字段 | 说明 |
|------|------|
| `enable` | 是否启用插件 / 模组 |
| `server_name` | 服务器名称，用于 Header `x-self-name` 与事件标识 |
| `access_token` | 鉴权 Token，留空则不验证 |
| `message_prefix` | 消息前缀，支持 MC 文本组件 JSON |
| `enable_translation` | 是否启用翻译功能 |
| `websocket_server` | 方式二（核心主动连接 MC 服务器）时启用，开放监听端口 |
| `websocket_client` | 方式一（MC 服务器主动连接核心）时启用，主动外连核心 |
| `rcon` | RCON 客户端配置 |
| `subscribe_event` | 订阅事件开关 |
| `ignored_commands` | 忽略的命令列表 |
:::

##### 翻译功能（可选）

启用 `enable_translation: true` 后，还需在 `config.yml` 同级目录下创建 `translate` 文件夹（插件端 `./plugins/QueQiao/translate/`，模组端 `./config/QueQiao/translate/`），放入 JSON 语言文件（如从客户端 jar 包提取的 `zh_cn.json`）。该功能可将成就、死亡事件中的翻译键转换为本地化文本。

#### 连接模式对接

鹊桥官方实现支持上文 [连接模式](#连接模式) 的两种方式，任选其一即可：

::: tabs
@tab 方式一：MC 服务器主动连接核心（推荐）

在 `websocket_client` 中启用，并在 `url_list` 中填写核心的 WebSocket 地址。MC 服务器主动外连核心，无需对外开放端口，适用于服务器在内网、无法暴露端口的场景，==是绝大多数场景下的推荐选择==。

**核心侧（`.env`）**

```ini
# 核心不主动外连，保持为空 {} 即可，不要填写任何地址
MINECRAFT_WS_URLS={}

# 鉴权 Token，与 MC 服务器端 access_token 保持一致
# 若 MC 服务器端 access_token 留空，则这里也留空
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC 服务器侧（`config.yml`）**

```yaml
server_name: "survival"          # 服务器名称，须与核心 MINECRAFT_WS_URLS 键名一致
access_token: "your_access_token" # 鉴权 Token，须与核心 MINECRAFT_ACCESS_TOKEN 一致

# 反向 WebSocket：MC 服务器主动外连核心
websocket_client:
  enable: true
  reconnect_interval: 5
  reconnect_max_times: 5
  url_list:
    - "ws://<核心IP>:8000/minecraft/ws"   # 核心的 WebSocket 地址

# 正向 WebSocket：本方式下关闭
websocket_server:
  enable: false
```

*其中端口 `8000` 为机器人核心监听端口（`.env` 的 `PORT`，默认 `8000`），路径固定为 `/minecraft/ws`。*

@tab 方式二：核心主动连接 MC 服务器

在 `websocket_server` 中启用并监听地址 / 端口，MC 服务器开放监听端口等待核心接入。适用于服务器能对外暴露端口、由核心主动连接的场景。

**核心侧（`.env`）**

```ini
# 键名为服务器名，值为 MC 服务器端 WebSocket 地址列表
# 键名须与 MC 服务器端 server_name 一致
MINECRAFT_WS_URLS={"survival": ["ws://<MC服务器IP>:8080/mc"]}

# 鉴权 Token，与 MC 服务器端 access_token 保持一致
# 若 MC 服务器端 access_token 留空，则这里也留空
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC 服务器侧（`config.yml`）**

```yaml
server_name: "survival"          # 服务器名称，须与核心 MINECRAFT_WS_URLS 键名一致
access_token: "your_access_token" # 鉴权 Token，须与核心 MINECRAFT_ACCESS_TOKEN 一致

# 正向 WebSocket：MC 服务器开放监听端口，等待核心接入
websocket_server:
  enable: true
  host: "0.0.0.0"
  port: 8080

# 反向 WebSocket：本方式下关闭
websocket_client:
  enable: false
```
:::

#### Header 鉴权

使用任一连接方式时，均需携带或校验以下 Header：

::: table title="Header 鉴权" copy="all"
| Header | 必填 | 说明 |
|--------|------|------|
| `x-self-name` | ::fluent-color:checkmark-circle-24:: | 服务器名称，必须与 `config.yml` 的 `server_name` 一致 |
| `Authorization` | ::fluent-color:warning-24:: | 鉴权，`Bearer <access_token>`，`access_token` 为空时可省略 |
| `x-client-origin` | ::fluent-color:warning-24:: | 对接项目来源标记，如 `minecraft` / `nonebot`，建议填写 |
:::

#### 游戏内命令

::: table title="游戏内命令" copy="all"
| 命令 | 权限节点 | 说明 |
|------|----------|------|
| `/queqiao help` | `queqiao.help` | 显示帮助 |
| `/queqiao reload` | `queqiao.reload` | 重载配置并重启 WebSocket |
| `/queqiao client reconnect [all]` | `queqiao.client.reconnect` | 重连 WebSocket Client（`all` 强制全部重连） |
:::

*Mod 端对权限的判定为 int Level，本模组所有命令权限定义为 `2`。*

### MCDR 端插件

鹊桥的 **MCDR 端插件** 运行在 MCDReforged 之上，负责将 Minecraft 服务器接入鹊桥协议。*该插件仅支持 MCDReforged 服务端。* 若使用 Spigot / Paper / Fabric / Forge / NeoForge 等其它服务端，请参阅上文 [鹊桥官方实现](#鹊桥官方实现)。

#### 功能特性

- **双模式 WebSocket**：支持客户端模式（主动连接）与服务端模式（被动监听）。
- **自动重连**：客户端模式可配置重连间隔与最大重试次数。
- **热重载**：`!!queqiao reload` 重载配置并复用旧连接，无需重启服务器。
- **游戏事件转发**：玩家加入 / 退出 / 聊天 / 命令 / 死亡 / 成就。
- **API 指令执行**：广播、私聊、Title、ActionBar、RCON 命令、状态查询。

#### 安装

::: tabs
@tab 方式一：直接下载 .mcdr 包

从 [Releases](https://github.com/Minecraft-UniBot/QueQiao.MCDReforged/releases) 下载 `queqiao-vX.X.X.mcdr`，放入 MCDR 的 `plugins/` 目录，重启 MCDR 即可。

@tab 方式二：源码安装

```bash
git clone https://github.com/Minecraft-UniBot/QueQiao.MCDReforged.git
cd MCDReforged
uv sync
```

将整个目录作为 Directory Plugin 放入 MCDR 插件目录，或自行打包：

```bash
uv run python -m mcdreforged pack
```
:::

##### 依赖

- **MCDReforged** ≥ 2.15.0
- **Python** ≥ 3.12
- Python 包：`websockets` ≥ 16.0、`PyYAML` ≥ 6.0、`psutil` ≥ 5.9
- MCDR 插件依赖：

::: table title="MCDR 插件依赖" copy="all"
| 插件 | 用途 | 必需 |
|------|------|------|
| [MoreGameEvents](https://mcdreforged.com/zh-CN/plugin/mg_events) | 玩家死亡、成就事件 | ::fluent-color:checkmark-circle-24:: |
| [Minecraft Data API](https://mcdreforged.com/zh-CN/plugin/minecraft_data_api) | 玩家坐标、生命值、经验等级 | ::fluent-color:checkmark-circle-24:: |
| [online_player_api](https://mcdreforged.com/zh-CN/plugin/online_player_api) | 在线玩家列表 | ::fluent-color:warning-24:: 可选（缺失时回退 MCDR 内置接口） |
:::

#### 配置

首次加载会在 `config/queqiao/config.json` 生成默认配置：

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

##### 字段说明

::: table title="config.json 字段说明" copy="all"
| 字段 | 说明 |
|------|------|
| `server_name` | 本服务器名称，用于 Header `x-self-name` 与事件标识 |
| `access_token` | 鉴权 Token，留空则不发送 `Authorization` 头 |
| `client_origin` | 客户端来源标识，默认 `mcdr` |
| `minecraft.host` / `minecraft.port` | MC 服务器地址，用于 Server List Ping。留空则自动从 MCDR 解析，解析不到时回退 `127.0.0.1:25565` |
| `client.enable` | 方式一（MC 服务器主动连接核心）时设为 `true` |
| `client.url` | 核心的 WebSocket 地址（方式一时填写） |
| `client.reconnect_interval` | 重连间隔（秒） |
| `client.reconnect_max_times` | 最大重连次数，`0` 表示无限重试 |
| `server.enable` | 方式二（核心主动连接 MC 服务器）时设为 `true` |
| `server.host` / `server.port` | WebSocket 监听地址（方式二时填写） |
| `log_events` | 是否在日志中打印事件转发记录 |
:::

#### 连接模式对接

MCDR 端插件支持上文 [连接模式](#连接模式) 的两种方式，任选其一即可：

::: tabs
@tab 方式一：MC 服务器主动连接核心（推荐）

将 `client.enable` 设为 `true`，并填写核心的 WebSocket 地址（`client.url`）。该模式下 MC 服务器主动连接核心，需与核心的 `server_name`、`access_token` 保持一致。

==推荐使用这种方式。== 当服务器在内网、无法直接对外暴露端口时，MC 服务器可主动外连，无需在服务器上开放监听端口。

**核心侧（`.env`）**

```ini
# 核心不主动外连，保持为空 {} 即可，不要填写任何地址
MINECRAFT_WS_URLS={}

# 鉴权 Token，与 MC 服务器端 access_token 保持一致
# 若 MC 服务器端 access_token 留空，则这里也留空
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC 服务器侧（`config.json`）**

```json
{
  "server_name": "survival",
  "access_token": "your_access_token",
  "client": {
    "enable": true,
    "url": "ws://<核心IP>:8000/minecraft/ws"
  },
  "server": {
    "enable": false
  }
}
```

*其中端口 `8000` 为机器人核心监听端口（`.env` 的 `PORT`，默认 `8000`），路径固定为 `/minecraft/ws`。*

@tab 方式二：核心主动连接 MC 服务器

将 `server.enable` 设为 `true`，插件将启动 WebSocket 服务端监听 `server.host:server.port`，等待核心接入。需在核心的 `MINECRAFT_WS_URLS` 中填写本插件的监听地址。

**核心侧（`.env`）**

```ini
# 键名为服务器名，值为 MC 服务器端 WebSocket 地址列表
# 键名须与 MC 服务器端 server_name 一致
MINECRAFT_WS_URLS={"survival": ["ws://<MC服务器IP>:8080/mc"]}

# 鉴权 Token，与 MC 服务器端 access_token 保持一致
# 若 MC 服务器端 access_token 留空，则这里也留空
MINECRAFT_ACCESS_TOKEN="your_access_token"
```

**MC 服务器侧（`config.json`）**

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

#### 命令

::: table title="命令列表" copy="all"
| 命令 | 权限 | 说明 |
|------|------|------|
| `!!queqiao` | 2 | 显示帮助 |
| `!!queqiao status` | 2 | 查看连接状态（模式、玩家、CPU、内存、MOTD 等） |
| `!!queqiao reload` | 2 | 重载配置并重新连接 |
:::

#### 基岩版（Bedrock）支持

本插件运行于 MCDReforged 之上，而 MCDR 通过**服务端处理器（Server Handler）**来管理不同类型的 Minecraft 服务端。借助 [Bedrock Liteloader Handler](https://mcdreforged.com/zh-CN/plugin/bedrock_liteloader_handler) 这一处理器，MCDR 可以直接托管 **基岩版专用服务器（BDS）**，从而让本插件也能将基岩版服务器接入鹊桥。

##### 原理

`bedrock_liteloader_handler` 是一个 MCDR 服务端处理器，它把 BDS 的标准输出解析为 MCDR 事件（玩家加入 / 退出 / 聊天等）。因此，本插件的事件转发（玩家进出、聊天）在基岩版服务器上**开箱即用**，无需改动插件代码。

##### 安装与配置

::: steps

1. **安装处理器**：从 [liteloader_handler Releases](https://github.com/Elec-Glacier/liteloader_handler/releases) 下载最新 `.mcdr` 包，放入 MCDR 的 `plugins/` 目录。

2. **安装本插件**：按上文 [安装](#安装-2) 安装鹊桥 MCDR 端插件。

3. **配置处理器**：启动 MCDR 后，在 `config/` 下生成处理器的配置文件，选择对应的基岩版处理器（默认即原版处理器），然后重载配置。

4. **配置鹊桥插件**：按上文 [配置](#配置-1) 填写 `config/queqiao/config.json`，`server_name` / `access_token` 与适配器保持一致。

:::

##### 聊天输出

原版 BDS **默认不输出玩家聊天**。要让玩家聊天事件被 MCDR 捕获并转发，需通过**行为包**或**修改服务端**的方式开启聊天输出，否则玩家聊天无法转发到鹊桥。

##### 已知限制

基岩版与 Java 版是两套不同的游戏，本插件部分能力在基岩版上存在差异：

::: table title="基岩版能力对照" copy="all"
| 能力 | Java 版 | 基岩版（BDS） |
|------|---------|---------------|
| 玩家加入 / 退出事件 | ✅ | ✅（经处理器解析） |
| 玩家聊天事件 | ✅ | ✅（需行为包 / 修改服务端开启输出） |
| 玩家死亡 / 成就事件 | ✅（MoreGameEvents） | ::fluent-color:warning-24:: 依赖 Java 事件，通常不可用 |
| 玩家坐标 / 生命值等数据 | ✅（minecraft_data_api） | ❌ 不可用，字段为 `None` |
| Server List Ping（MOTD / 在线数） | ✅（Java SLP 协议） | ❌ 基岩版使用 RakNet 协议，ping 失败，`get_status` 回退 |
| 广播 / 私聊（`tellraw`） | ✅ | ::fluent-color:warning-24:: 命令语法不同，需适配 |
| Title / ActionBar | ✅ | ::fluent-color:warning-24:: 命令语法不同（如 `titleraw`） |
| RCON 命令 | ✅ | ::fluent-color:warning-24:: 命令集不同 |
:::

*由于基岩版与 Java 版命令体系差异较大，若需在基岩版上使用广播、私聊、Title 等 API，建议在 [QueQiao.MCDReforged](https://github.com/Minecraft-UniBot/QueQiao.MCDReforged) 仓库中提出需求或提交适配。*

##### 注意事项

- **LeviLamina**：LeviLamina 1.0.0 之后 MCDR 无法直接获取修改过的服务端输出，需借助支持 pty 的应用作为桥梁（详见 [liteloader_handler#13](https://github.com/Elec-Glacier/liteloader_handler/issues/13)）。
- **Unicode 修复**：受 [BDS-3791](https://bugs.mojang.com/browse/BDS-3791) 影响，中文等非 ASCII 字符可能显示异常，可安装 [UnicodeFixer](https://www.minebbs.com/resources/unicodefixer.6991/) 修复。
- **插件兼容性**：基岩版与 Java 版判若两个游戏，使用其它 MCDR 插件前请确认其是否兼容基岩版。

## 数据模型

适配器提供以下核心类型：

- `Bot`：机器人实例
- `Message` / `MessageSegment`：消息对象
- `Adapter`：适配器类
- 各类事件模型（玩家事件、聊天事件等）

## 开发调试

你可以在 `tests/` 目录下运行适配器的测试套件：

```bash
uv run pytest
```

## 贡献与支持

- 使用问题请提交 [Issues](https://github.com/17TheWord/nonebot-adapter-minecraft/issues)
- 代码贡献欢迎提交 [Pull requests](https://github.com/17TheWord/nonebot-adapter-minecraft/pulls)