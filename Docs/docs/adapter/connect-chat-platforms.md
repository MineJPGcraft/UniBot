# 接入聊天平台

UniBot 基于 NoneBot2，通过安装不同的适配器接入各聊天平台。本页介绍各平台适配器的配置字段与对接方式，所有配置均在 UniBot 根目录的 `.env` 中完成。

::: note 使用 WebUI 可直接创建机器人卡片填写
若已启用 [WebUI](/guide/features.html)，==无需手动编辑 `.env`==：登录后进入 **配置 → 环境变量**，各平台的机器人列表字段（如 `QQ_BOTS`、`TELEGRAM_BOTS`、`DISCORD_BOTS` 等）会以**机器人卡片**形式呈现。点击 **添加一项** 即可创建机器人卡片，逐项填写 `token`、`secret` 等字段，支持展开 / 折叠、拖动排序与删除。填写完成后保存，重启机器人生效。
:::

*注意：列表 / 对象类型的配置请使用 JSON 格式，并用双引号包裹整个值。* 未安装的适配器配置不会被加载。

## 公共框架配置

在配置各平台前，先确认以下框架级配置：

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

# 驱动类型（FastAPI）
DRIVER=~fastapi
```

*如需公网连接，请将 `HOST` 改为 `0.0.0.0`。*

## QQ 官方机器人（推荐）

通过 QQ 开放平台接入，机器人列表需在开放平台申请应用后获得 AppID / Token / Secret。

::: tip
若版本 ==高于 `v1.0.3`== 则你可以在 `WebUi` 的配置页面 `增加机器人` 卡片上方找到扫码直接登录的按钮。
:::

```ini
QQ_BOTS=[]
QQ_IS_SANDBOX=false
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `QQ_BOTS` | 机器人配置列表（JSON 数组），每项含 `id`、`token`、`secret`、`intent`、`use_websocket` 等字段 |
| `QQ_IS_SANDBOX` | 是否启用沙盒模式，默认 `false` |
:::

`QQ_BOTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `id` | 应用 AppID（开放平台获取） |
| `token` | 应用 Token |
| `secret` | 应用 Secret |
| `intent` | 事件订阅（对象类型），可选字段如 `guilds`、`guild_messages`、`at_messages` 等，默认值见官方文档 |
| `use_websocket` | 是否使用 WebSocket 连接，默认 `True`；`False` 时使用 WebHook（需公网） |
:::

## OneBot V11（QQ）

OneBot V11 是 QQ 的通用协议，需配合 **[SnowLuma](https://snowluma.github.io/)、NapCat、LLOneBot** 等协议端使用。

```ini
# OneBot 平台的 AccessToken，由 OneBot 服务端设置；未启用请留空
ONEBOT_ACCESS_TOKEN=""
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `ONEBOT_ACCESS_TOKEN` | OneBot 服务端设置的访问令牌，未启用留空 |
:::

*如有多个反向连接，可用 `ONEBOT_WS_URLS` 等字段，具体参考 OneBot 适配器文档。* 协议端作为服务端（反向 WebSocket）时，UniBot 会主动连接；具体对接方式见 [OneBot V11 适配器文档](https://onebot.adapters.nonebot.dev/)。

## Telegram

通过官方 Bot API 接入，机器人 Token 向 [@BotFather](https://t.me/BotFather) 申请。

```ini
TELEGRAM_BOTS=[]
TELEGRAM_WEBHOOK_URL=""
TELEGRAM_PROXY=""
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `TELEGRAM_BOTS` | 机器人配置列表（JSON 数组），每项含 `token`、`is_webhook` 字段 |
| `TELEGRAM_WEBHOOK_URL` | Webhook 模式下使用的公网 HTTPS 地址；Long polling 模式下留空 |
| `TELEGRAM_PROXY` | 访问 Telegram API 的代理地址，如 `http://127.0.0.1:10809`；Socks 协议需安装 `httpx[socks]` |
:::

`TELEGRAM_BOTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `token` | 向 @BotFather 申请的机器人 Token（必填） |
| `is_webhook` | 是否启用 Webhook 模式，默认 `false`（即默认 Long polling 模式） |
:::

## Discord

通过官方 Bot 接入，机器人 Token 在 [Discord Developer Portal](https://discord.com/developers/applications) 创建应用后获取。

```ini
DISCORD_BOTS=[]
DISCORD_API_VERSION=10
DISCORD_API_TIMEOUT=30
DISCORD_COMPRESS=false
DISCORD_HANDLE_SELF_MESSAGE=false
DISCORD_PROXY=""
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `DISCORD_BOTS` | 机器人配置列表（JSON 数组），每项含 `token`、`intent`、`application_commands` 字段 |
| `DISCORD_API_VERSION` | Discord API 版本，默认 `10` |
| `DISCORD_API_TIMEOUT` | Discord API 超时时间（秒），默认 `30` |
| `DISCORD_COMPRESS` | 是否启用网关数据压缩，默认 `false` |
| `DISCORD_HANDLE_SELF_MESSAGE` | 是否处理自己发送的消息，默认 `false` |
| `DISCORD_PROXY` | 访问 Discord API 的代理地址，不使用留空 |
:::

`DISCORD_BOTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `token` | 机器人 Token（必填） |
| `intent` | 事件订阅（对象类型），常用字段：`guild_messages`、`direct_messages`、`message_content`（特权 Intent，需在 Developer Portal 开启） |
| `application_commands` | 斜杠命令注册范围；`{"*": ["*"]}` 注册全部为全局命令，`{"命令名": ["服务器ID"]}` 注册为指定服务器的局部命令 |
:::

## DoDo

通过 DoDo 开放平台接入，仅支持 WebSocket 连接。

```ini
DODO_BOTS=[]
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `DODO_BOTS` | 机器人配置列表（JSON 数组），每项含 `client_id`、`token` 字段 |
:::

`DODO_BOTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `client_id` | 开放平台获取的客户端 ID（必填） |
| `token` | 开放平台获取的客户端 Token（必填） |
:::

## KOOK（开黑啦）

通过 KOOK 开发者平台接入，机器人 Token 在开发者平台的应用中获取。

```ini
KAIHEILA_BOTS=[]
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `KAIHEILA_BOTS` | 机器人配置列表（JSON 数组），每项含 `token` 字段 |
:::

`KAIHEILA_BOTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `token` | 在开发者平台 - 我的应用 - 机器人页面获取的 Token（必填） |
:::

## Satori

Satori 是通用协议，可对接 Chronocat 等实现了 Satori 协议的平台。

```ini
SATORI_CLIENTS=[]
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `SATORI_CLIENTS` | Satori 客户端列表（JSON 数组），每项含 `host`、`port`、`path`、`token`、`timeout`、`secure` 字段 |
:::

`SATORI_CLIENTS` 每项字段：

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `host` | Satori 服务端监听地址，如 `localhost`（必填） |
| `port` | Satori 服务端监听端口，如 `5500`（必填） |
| `path` | Satori 服务端自定义监听路径，如 `/satori`，默认空字符串 |
| `token` | 连接令牌，由服务端决定是否需要（如对接 Chronocat 必填） |
| `timeout` | 连接超时时间（秒），默认 `30` |
| `secure` | 是否使用 TLS 加密连接，默认 `false` |
:::

## Minecraft

通过 [鹊桥](/adapter/) 协议与 Minecraft 服务器互通，具体对接见 [Minecraft 适配器](/adapter/usage.html)。

```ini
# Minecraft WebSocket 地址（支持多服）
MINECRAFT_WS_URLS={"server1": ["ws://127.0.0.1:8080/mc"]}

# 服务器接入鉴权 Token
MINECRAFT_ACCESS_TOKEN=""
```

::: table copy="all"
| 字段 | 说明 |
|------|------|
| `MINECRAFT_WS_URLS` | 服务器名 → WebSocket 地址列表（JSON 对象），支持多服 |
| `MINECRAFT_ACCESS_TOKEN` | 服务器接入鉴权 Token，须与服务器端一致 |
:::

## 配置校验

配置完成后，重启机器人生效。若某平台未配置对应字段，则该适配器不会启用。各平台的具体对接流程与协议端安装，请参阅对应适配器的官方文档。