# 指令手册

UniBot 的指令基于 [Alconna](https://github.com/ArcletProject/Alconna) 解析，跨平台表现一致。默认命令前缀为 `/`（可在 `.env` 的 `COMMAND_START` 中修改）。

*所有指令均受 `Config.toml` 中的 `command_groups`（指令群）与 `command_enabled`（启用列表）控制。*

## 指令总览

::: table title="指令总览" copy="all"
| 指令 | 功能 | 权限 |
|------|------|------|
| `/list` | 查询所有服务器的在线玩家 | 所有用户 |
| `/server` | 查看当前连接的服务器列表 | 所有用户 |
| `/luck` | 每日运势占卜 / 运势排行（仅供娱乐） | 所有用户 |
| `/send` | 向游戏内发送消息 | 所有用户 |
| `/command` | 远程执行 Minecraft 指令 | <Badge type="danger" text="管理员" /> |
| `/bound` | 绑定 / 解绑 / 查询游戏白名单 | 所有用户 |
| `/help` | 查看命令帮助 | 所有用户 |
| `/bot` | 机器人管理（关于 / 检查更新 / 更新 / 重启 / 超级用户） | 混合（见下） |
:::

## 详细说明

### `/list` — 在线玩家

查询所有已连接服务器的在线玩家列表，支持通过参数指定服务器。

```
/list                # 查询所有服务器
/list <服务器名称>    # 查询指定服务器
```

- 玩家按「玩家」与「假人」分类展示（根据 `bot_prefix` 判断）。
- 启用图片模式时，会渲染为带玩家头像的精美图片。

### `/server` — 服务器列表

查看当前连接的服务器列表与状态。

```
/server
```

### `/luck` — 每日运势

每日运势占卜，仅供娱乐；`rank` 子命令可查看今日运势排行。

```
/luck              # 查看今日运势
/luck rank         # 查看今日运势排行
```

- 运势结果由「日期 + 群 + 用户」生成的种子决定，同一天内重复查看结果一致。
- 排行仅统计已绑定白名单的玩家，按人品值从高到低排列，跨天自动清空。
- 启用图片模式时，会渲染为精致的运势卡片 / 排行图片。

### `/send` — 消息发送

往游戏内发送消息（在 `sync_all_qq_message` 关闭时可用）。

```
/send <消息内容>
```

### `/command` — 远程指令

远程执行 Minecraft 指令（需管理员权限）。

```
/command <服务器> <指令>
```

- 受 `command_minecraft_whitelist` 与 `command_minecraft_blacklist` 控制。
- 例如 `/command server1 say hello` 会在 server1 上执行 `say hello`。

### `/bound` — 白名单绑定

绑定 / 解绑 / 查询游戏白名单。

```
/bound                # 查看自己的绑定
/bound <玩家名称>      # 绑定白名单
/bound remove <玩家名称>  # 解绑
/bound remove --all   # 解绑全部
```

- 玩家名称只能包含字母、数字、下划线，长度不超过 16 个字符。
- 绑定数量受 `qq_bound_max_number` 限制。

### `/help` — 帮助

查看可用命令列表，或查看指定命令的详细帮助。

```
/help              # 列出所有命令
/help <命令名称>    # 查看指定命令详情
```

### `/bot` — 机器人管理

机器人管理入口，集成了关于信息、版本检查、更新、重启与超级用户管理。

```
/bot about                    # 查看关于信息（版本 / 更新状态 / 项目链接）
/bot check                    # 主动检测新版本
/bot update                   # 拉取最新代码并自动重启（需管理员）
/bot restart                  # 重启机器人（需管理员）
/bot superusers add <@用户/ID>     # 添加超级用户（需管理员）
/bot superusers remove <@用户/ID>  # 移除超级用户（需管理员）
```

::: table title="/bot 子命令权限" copy="all"
| 子命令 | 功能 | 权限 |
|--------|------|------|
| `about` | 关于信息（版本 / 更新状态 / 项目链接） | 所有用户 |
| `check` | 主动检测是否有新版本 | 所有用户 |
| `update` | 拉取最新代码并自动重启（基于 git pull） | <Badge type="danger" text="管理员" /> |
| `restart` | 通过守护进程重启机器人 | <Badge type="danger" text="管理员" /> |
| `superusers add/remove` | 增删超级用户，写回 `.env` | <Badge type="danger" text="管理员" /> |
:::

常用示例：

```
/bot about                     # 查看关于信息
/bot check                     # 检测新版本
/bot superusers add @某某       # 添加超级用户
/bot superusers remove 123456  # 移除超级用户
```

- `superusers` 支持 `@用户` 或直接填用户 ID。
- `update` 依赖 git 部署（通过 `git pull --ff-only` 拉取最新代码），仅当实际拉取到新提交时才重启；非 Watchdog 启动时提示无法自动更新。
- `restart` / `update` 需由 Watchdog 守护进程启动（`Watchdog.py`），否则提示无法自动执行。
- `superusers` 改动即时生效，但框架层权限需重启后完全生效（与旧 `/config` 行为一致）。

## 平台前缀

指令在不同平台响应相同的群格式，通过前缀区分平台：

::: table title="平台前缀" copy="all"
| 平台 | 前缀 |
|------|------|
| QQ 客户端 | `qq_client` |
| QQ 频道 | `qq_guild` |
| QQ API | `qq_api` |
| Telegram | `telegram` |
| Discord | `discord` |
| Kook | `kook` |
:::

在 `command_groups` / `message_groups` 中按 `"{平台}:{群ID}"` 格式填写。