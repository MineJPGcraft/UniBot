---
title: 配置指南
date: 2026-08-04
description: Minecraft UniBot 配置详解：.env 框架配置与 Config.toml 业务配置的双文件体系，覆盖端口、指令、图片渲染、WebUI 等全部配置项说明。
---

# 配置指南

UniBot 采用 **双配置文件** 体系，分别管理框架层与业务层配置，各司其职。

## 配置文件概览

::: table title="配置文件概览" copy="all"
| 文件 | 位置 | 用途 | 格式 |
|------|------|------|------|
| `.env` | 项目根目录 | NoneBot 框架配置与适配器配置 | INI 风格 |
| `Config.toml` | 项目根目录 | 机器人自定义配置（指令、消息、图片等） | TOML |
| `Config/Extensions.toml` | `Config/` 目录 | 扩展启停开关（每扩展一个键） | TOML |
| `Config/Extensions/<id>.toml` | `Config/Extensions/` 目录 | 各扩展的独立配置（每扩展一个文件） | TOML |
| `Config/Messages.zh.toml` / `Config/Messages.en.toml` | `Config/` 目录 | 机器人消息双语包（按 `language` 加载） | TOML |
:::

==日常使用中，绝大多数配置都能在 WebUI 里可视化完成，无需手动编辑这些文件。== 本页面向需要深入调整或手动部署的场景。

---

## `.env` — 框架与适配器

`.env` 用于配置 NoneBot 框架本身，以及各平台的适配器。

### 框架配置

::: collapse expand
- 配置示例

  ```ini
  # 监听端口与主机
  PORT=8000
  HOST="127.0.0.1"

  # 超级用户（管理员账号，可多个）
  SUPERUSERS=["1234567890"]

  # 命令起始字符与分隔符
  COMMAND_START=["#"]
  COMMAND_SEP=[" "]

  # 日志级别
  LOG_LEVEL="INFO"
  ```
:::

### Minecraft 服务器配置

```ini
# Minecraft WebSocket 地址（支持多服）
# 格式：{服务器名}: [{地址列表}]
MINECRAFT_WS_URLS={"server1": ["ws://127.0.0.1:8080/mc"]}

# 服务器接入鉴权 Token（需与鹊桥插件一致）
MINECRAFT_ACCESS_TOKEN=""
```

### 平台适配器配置

以 OneBot V11（QQ）为例：

```ini
# OneBot 连接方式（forward / ws / reverse 等）
ONEBOT_ACCESS_TOKEN=""
ONEBOT_WS_URLS=["ws://127.0.0.1:6700"]
```

其他平台（Telegram、Discord、Kook 等）可参考对应适配器的文档，在 `.env` 中配置对应的 `BOT_TOKEN` 等字段。

---

## `Config.toml` — 机器人配置

`Config.toml` 是机器人业务层的主要配置，采用 TOML 格式。嵌套表会自动展平成配置字段（例如 `[webui]` 下的 `enabled` → `webui_enabled`）。

### 基础配置

::: collapse expand
- 配置示例

  ```toml
  # 机器人消息语言：zh / en，决定加载哪个 Messages 消息包
  # 仅影响机器人发送的消息；WebUI 面板语言在面板内独立切换
  language = "zh"

  # 是否将所有的管理员视为超级用户
  admin_superusers = true

  # 假人前缀，list 指令的分类依据，以及进服广播的判定依据
  # 无假人或不想分类时留空
  bot_prefix = ""

  # 指令群：机器人只响应这些群的指令
  # 格式 "{平台}:{群ID}"
  command_groups = ["qq_client:123456789"]

  # 消息群：发送消息到游戏、以及同步游戏消息到群的群
  message_groups = ["qq_client:123456789"]

  # 可通过指令远程执行的命令白名单 / 黑名单
  command_minecraft_whitelist = []
  command_minecraft_blacklist = ["kill"]
  ```
:::

::: note 更快的授权方式
`command_groups` / `message_groups` / `SUPERUSERS` 也可以通过 WebUI「快速开始」引导的**令牌授权**自动完成：在任意平台群聊中发送认证令牌即可。详见 [功能特性](/guide/features.html)。
:::

### 消息同步

::: collapse expand
- 配置示例

  ```toml
  # 是否播报服务器开启/关闭
  broadcast_server = true

  # 是否播报玩家进入/离开
  broadcast_player = true

  # 是否把消息群内的所有消息转发到服务器内
  sync_all_qq_message = true

  # 是否把服务器内消息转发到 QQ 群
  sync_all_game_message = false

  # 是否把服务器内消息转发到其他服务器
  sync_message_between_servers = false

  # 敏感词过滤（命中后不转发，并提醒违禁）
  sync_sensitive_words = ["敏感词", "你妈", "色图"]

  # 转发消息颜色（支持 16 种 MC 颜色或 #hex）
  sync_color_source = "gray"
  sync_color_player = "gray"
  sync_color_message = "gray"

  # 绑定 QQ 号的最大数量，0 表示不限制
  qq_bound_max_number = 1
  ```
:::

### 白名单配置

```toml
# 白名单指令名称
whitelist_command = "whitelist"

# 获取玩家列表的兼容模式（监听玩家进出更新，可能不准确）
list_compatible_mode = false
```

### WebUI 管理面板

```toml
[webui]
# 是否启用 WebUI（需额外安装 webui 依赖）
enabled = true
```

### 图片渲染

图片渲染的 `[image]` 配置、启用步骤与外观调整，见 [图片渲染](/guide/image-rendering.html)。

---

## `Config/Extensions.toml` — 扩展启停

该文件记录每个扩展是否启用，由 WebUI 或机器人自动维护，一般无需手动编辑。

```toml
[Default]
enabled = true

# 图片模式所需的渲染引擎与默认模板扩展（随官方市场分发，安装后自动登记）
[Html2Pic]
enabled = true
```

---

## `Config/Extensions/` — 扩展配置

每个启用配置的扩展对应一个独立配置文件 `Config/Extensions/<扩展ID>.toml`。扩展在清单中声明了配置项后，文件会自动创建，包含全部配置项的默认值；在 WebUI 或机器人中修改后自动写回。

修改配置后，扩展会立即校验并生效；校验失败时保留原配置不变。

---

## `Config/Messages.zh.toml` / `Config/Messages.en.toml` — 消息文本

机器人的所有对外提示/播报文本均集中于消息包文件，支持 `{占位符}` 格式化；在 WebUI 保存后立即热生效。

- `language = "zh"` 时加载 `Messages.zh.toml`（旧版单文件 `Messages.toml` 会自动作为中文包兼容回退）
- `language = "en"` 时加载 `Messages.en.toml`
- 两份语言包含完全相同的键，可分别自定义；切换语言通过 `Config.toml` 的 `language` 字段

```toml
[events]
player_join = "玩家 {player} 加入了游戏。"        # en 包: "Player {player} joined the game."

[commands.send]
sent = "已向服务器发送消息：{content}。"

[commands.luck]
result = "你今天的人品为 {point}，{tips}"
```

*注意：请勿删除已有键。* 缺失必填项将导致机器人启动失败。

::: tip 隐藏区块（# Hidden Start / # Hidden End）
消息包中 `# Hidden Start` 与 `# Hidden End` 两行注释连同其之间的内容**完全不会出现**在 WebUI「消息文本」编辑器中：
保存时自动按原位置并回（依据区块前方的可见内容定位）、机器人照常加载。
若区块前的定位内容被删除，该区块会在保存时以完整标记对追加到文件末尾，数据不会丢失。
请勿在 WebUI 编辑器中手动输入这两个标记（会被忽略）。
:::

::: tip 界面语言与消息语言相互独立
WebUI 管理面板的界面语言（中/英）在面板右上角切换、仅保存在浏览器本地；
机器人 API 返回的动态提示会跟随浏览器语言自动切换，均与 `language` 字段无关。
:::

---

## 依赖与可选功能

不同的可选功能需要额外的依赖，请在启用前同步对应的 extra：

```bash
# WebUI 管理面板
uv sync --extra webui --inexact

# 扩展依赖（已启用扩展声明的 Python 依赖，聚合自各扩展清单）
uv sync --extra extensions --inexact
```

==启用某个功能前，先确认对应的 extra 已安装==，否则该功能无法正常工作。

图片渲染的 Python 依赖由**渲染引擎扩展自身声明**（`Extension.toml` 的 `[dependencies].python`），安装扩展后通过 `extensions` extra 统一同步，==无需单独的 image extra==。

*Watchdog 会自动检测配置变化并同步对应的依赖。*