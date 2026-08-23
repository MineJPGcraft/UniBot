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
| `Config/Messages.toml` | `Config/` 目录 | 对外发送的消息文本（可自定义） | TOML |
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

### 图片渲染模式

图片渲染能力由**渲染引擎、模板、资源**三类扩展协作提供，均以扩展形式从**扩展市场**分发，可按需安装、自由组合。官方提供了开箱即用的组合：

::: table title="官方渲染相关扩展" copy="all"
| 扩展 | 类型 | 说明 |
|------|------|------|
| `Html2Pic` | 渲染引擎 | HTML 转图片渲染引擎 |
| `Default` | 模板 & 资源 | 默认指令的图片模板与资源包 |
:::

#### 启用图片模式

::: steps

1. **安装渲染相关扩展**

   在 WebUI 扩展市场中安装 ==**`Html2Pic`**==（渲染引擎）与 ==**`Default`**==（默认模板 & 资源）。开启图片模式时若缺失，WebUI 也会弹窗引导自动下载。

2. **启用并选择渲染配置**

   在 `Config.toml` 的 `[image]` 节设置 `mode = true`，并指定要使用的渲染引擎与模板：

   ```toml
   [image]
   # 是否启用图片模式（需安装上述渲染相关扩展）
   mode = false

   # 使用的渲染引擎（对应已安装的渲染引擎扩展，如 Html2Pic）
   # 修改后需重启机器人；未选择或引擎不可用时渲染会报错
   renderer = ""

   # 使用的模板包（对应已安装的模板扩展，默认 "Default"）
   # 修改后立即生效，无需重启；缺失时自动回退默认模板
   template = "Default"

   # 自定义字体文件路径（可选）；留空自动从资源扩展根目录查找 Font.ttf
   # font = ""
   ```

3. **重启机器人**

   `mode` 与 `renderer` 修改后需==**重启**==生效；`template` 切换==**即时生效**==，无需重启。

:::

渲染引擎与模板也可在 **WebUI → 扩展管理** 中直接切换。

- ==模板自动回退==：当前模板包缺失或不可用时，自动回退到默认模板（`Default` 或首个可用模板）。
- ==渲染引擎需显式选择==：图片模式必须安装并选择一个可用的渲染引擎扩展；引擎未选择或不可用时，渲染会报错提示。

#### 调整图片外观

图片的背景、配色、字体等外观由**模板扩展**提供，不在核心 `Config.toml` 中配置：

- 模板扩展可在其清单中声明外观配置项（如主色、字体、布局等）。
- 在 **WebUI → 扩展管理** 中选中对应模板扩展，通过表单修改并保存后**立即生效**；也可直接编辑 `Config/Extensions/<模板ID>.toml`。
- 更换模板包即可整体切换图片风格。

*注意：图片模式会略微增加指令响应时间。*

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

## `Config/Messages.toml` — 消息文本

机器人的所有对外提示/播报文本均集中于此文件，支持 `{占位符}` 格式化，修改后重启生效。

```toml
[events]
player_join = "玩家 {player} 加入了游戏。"
player_join_group = "玩家 {player} 加入了 [{server}] 服务器，喵～"

[commands.send]
sent = "已向服务器发送消息：{content}。"

[commands.luck]
result = "你今天的人品为 {point}，{tips}"
```

*注意：请勿删除已有键。* 缺失必填项将导致机器人启动失败。

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