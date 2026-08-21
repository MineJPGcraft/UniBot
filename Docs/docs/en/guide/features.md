# Features

UniBot offers a rich set of features, covering group-server interop, image rendering, WebUI management, and more.

## Group-Server Interop

UniBot's core capability is letting Minecraft and chat platforms communicate *in real time*:

- ::fluent-color:checkmark-circle-24:: See QQ group messages in-game in real time
- ::fluent-color:checkmark-circle-24:: See in-game chat in QQ groups, supporting message types like text and images
- ::fluent-color:checkmark-circle-24:: Broadcasts of all player **join / leave / death** events
- ::fluent-color:checkmark-circle-24:: Automatic notifications of server **start / stop**
- ::fluent-color:checkmark-circle-24:: Cross-server message relay, building a distributed MC network

### Message Sync Directions

::: table title="Message Sync Directions" copy="all"
| Direction | Config Item | Description |
|------|--------|------|
| Group → Server | `sync_all_qq_message` | Group messages are automatically forwarded to the game |
| Server → Group | `sync_all_game_message` | In-game messages are automatically forwarded to the group |
| Server → Server | `sync_message_between_servers` | Cross-server message relay |
:::

### Event Broadcast

Supported broadcast events:

- Player join / leave
- Player death
- Player achievements
- Server start / stop

*The player death and achievement events require the [MoreGameEvents](https://mcdreforged.com/zh-CN/plugin/mg_events) plugin on the MCDR side.*

### Sensitive Word Filtering

Through the `sync_sensitive_words` configuration, messages that hit a sensitive word are not forwarded to the group; instead, a violation reminder is sent.

---

## Image Rendering Mode

After setting `[image] mode` to `true` in `Config.toml`, the bot's command output will be sent in **image** form.

The rendering system consists of three mutually independent parts that can be freely combined:

::: table title="Rendering System Components" copy="all"
| Component | Role | Description |
|------|------|------|
| **Rendering engine** | Renders a page into an image | Determines the rendering implementation, e.g. the built-in rendering engine (default) |
| **Template** | Determines the layout and style of the image | Each template is an image style that can be switched at any time |
| **Resource** | Provides the static assets needed for images | Background images, avatar placeholders, etc., applied together with the template |
:::

- **Template switching takes effect immediately**: after switching templates in WebUI or the config, you can see the new style without restarting.
- **Rendering engine switching requires a restart**: after changing the rendering engine, restart the bot; it falls back to the default engine until the restart.
- **Default fallback supported**: when the current template or engine is unavailable, it automatically falls back to the built-in default, so usage is not affected.

### Commands with Image Rendering Support

::: table title="Commands with Image Rendering Support" copy="all"
| Command | Rendered Content |
|------|----------|
| `/list` | Online player list (including player avatars) |
| `/server` | Server connection status |
| `/luck` / `/luck rank` | Daily fortune card / fortune leaderboard |
| `/bound` | Whitelist binding information |
| `/help` | Help information |
| `/bot about` | About page |
| `/bot check` | Version check result |
:::

### Image Appearance Configuration

You can adjust the image appearance in the `[image]` section of `Config.toml`:

```toml
[image]
mode = true
# Use a local image
background = 'url("./Resources/Backgrounds/dirt.png")'

# Use a gradient
background = 'linear-gradient(150deg, #2e4a30 0%, #1d3524 55%, #12241a 100%)'

# Pick a random image from the directory
background = 'random("./Resources/Backgrounds/")'
```

You can also use the `renderer` and `template` config items to specify the rendering engine and template to use (they automatically appear in the selection list once the corresponding extensions are installed). *Note: image mode slightly increases response time.*

---

## WebUI Admin Panel

UniBot ships with a web admin panel built on **Vue 3 + Vite**, interacting with the backend through a REST API. It provides real-time dashboard monitoring, server / player management, visual configuration, extension management, log viewing, and more — **with WebUI, you'll basically never need to manually edit configuration files**.

- **Dashboard**: real-time running status + "Quick Start" guide card
- **Visual configuration**: grouped editing of `Config.toml` / `.env` / `Messages.toml` with Schema validation
- **Server / Player / Adapter / Plugin / Extension**: one-stop management
- **Log viewing**: real-time WebSocket streaming + level filtering
- **Login authentication**: JWT + HttpOnly Cookie, admin account system

::: note
Detailed explanations of each page, how to enable it, initializing the admin, and FAQ, see **[WebUI Admin Panel](/en/guide/webui.html)**.
:::

---

## Extension System

UniBot is built on **NoneBot2** and seamlessly integrates with the [NB plugin registry](https://registry.nonebot.dev/) — community plugins work out of the box; the built-in extension mechanism lets you freely combine bot capabilities like building blocks:

- **Five extension types**: command, service, rendering engine, template, and resource — install and enable/disable on demand.
- **Out of the box**: built-in commands and templates are preinstalled, no additional configuration needed.
- **Stable and reliable**: an exception in a single extension won't bring down the whole bot; a failing extension is automatically isolated with the reason noted.
- **Dependency aware**: dependencies between extensions are resolved automatically, with clear notifications about missing or version-incompatible dependencies.
- **Visual management**: enable/disable extensions, configure them, and switch rendering engines / templates right in WebUI.

For more details, see [Extension System](/en/unibot/extension-system.html).

---

## Whitelist Management

A complete binding system between platform accounts and game IDs:

- Supports whitelist sync across multiple servers.
- Configurable binding count (`qq_bound_max_number`).
- Manageable directly with the `/bound` command.

---

## Comparison with Similar Solutions

::: table title="Comparison with Similar Solutions" copy="all" hl-cols="success:2"
| Feature | **UniBot** | Traditional Solutions |
|------|-----------|---------|
| Multi-platform support | ::fluent-color:checkmark-circle-24:: QQ / Telegram / Discord / Kook… | ::fluent-color:dismiss-circle-24:: Usually QQ only |
| Multi-server interconnection | ::fluent-color:checkmark-circle-24:: Native support, message relay | ::fluent-color:dismiss-circle-24:: Requires self-modification |
| WebSocket communication | ::fluent-color:checkmark-circle-24:: Real-time persistent connection | ::fluent-color:warning-24:: Mostly HTTP polling |
| Extension system | ::fluent-color:checkmark-circle-24:: Command / service / rendering / template / resource — plug-and-play | ::fluent-color:dismiss-circle-24:: Monolithic coupling |
| NoneBot2 ecosystem | ::fluent-color:checkmark-circle-24:: Seamless access to the NB plugin registry | ::fluent-color:dismiss-circle-24:: Closed-source self-developed |
| WebUI | ::fluent-color:checkmark-circle-24:: Vue 3 admin panel | ::fluent-color:dismiss-circle-24:: None |
| Image rendering | ::fluent-color:checkmark-circle-24:: HTML/CSS template engine | ::fluent-color:dismiss-circle-24:: None |
| Whitelist management | ::fluent-color:checkmark-circle-24:: Complete binding system | ::fluent-color:dismiss-circle-24:: None or basic |
:::