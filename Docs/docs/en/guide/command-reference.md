---
title: "Command Reference"
date: 2026-08-21
description: "Complete command reference for Minecraft UniBot: command overview, detailed usage, platform prefix differences, custom prefixes, and toggling commands per platform via command groups."
tags:
  - commands
  - reference
  - Alconna
---

# Command Reference

UniBot's commands are parsed with [Alconna](https://github.com/ArcletProject/Alconna) and behave consistently across platforms. The default command prefix is `/` (configurable in `COMMAND_START` in `.env`).

*All commands are controlled by `command_groups` (command groups) and `command_enabled` (enable list) in `Config.toml`.*

## Command Overview

::: table title="Command Overview" copy="all"
| Command | Function | Permission |
|------|------|------|
| `/list` | Query online players on all servers | All users |
| `/server` | View the list of currently connected servers | All users |
| `/luck` | Daily fortune fortune-telling / fortune ranking (for entertainment only) | All users |
| `/send` | Send a message into the game | All users |
| `/command` | Execute Minecraft commands remotely | <Badge type="danger" text="Admin" /> |
| `/bound` | Bind / unbind / query game whitelist | All users |
| `/help` | View command help | All users |
| `/bot` | Bot management (about / check update / update / restart / superuser) | Mixed (see below) |
:::

## Detailed Descriptions

### `/list` — Online Players

Query the online player lists of all connected servers, with support for specifying a server via a parameter.

```
/list                # Query all servers
/list <server name>    # Query the specified server
```

- Players are shown grouped into "players" and "fake players" (determined by `bot_prefix`).
- When image mode is enabled, a nice image with player avatars is rendered.

### `/server` — Server List

View the list and status of currently connected servers.

```
/server
```

### `/luck` — Daily Fortune

Daily fortune fortune-telling, for entertainment only; the `rank` subcommand shows today's fortune leaderboard.

```
/luck              # View today's fortune
/luck rank         # View today's fortune leaderboard
```

- The result is derived from a seed based on the date, group, and user ID, so repeated queries on the same day return the same result.
- The leaderboard only counts players with a bound whitelist, sorted by fortune score from high to low, and resets automatically each day.
- When image mode is enabled, a fortune card / leaderboard image is rendered.

### `/send` — Send Message

Send a message into the game (available when `sync_all_qq_message` is disabled).

```
/send <message content>
```

### `/command` — Remote Commands

Execute Minecraft commands remotely (requires admin permission).

```
/command <server> <command>
```

- Controlled by `command_minecraft_whitelist` and `command_minecraft_blacklist`.
- For example, `/command server1 say hello` executes `say hello` on server1.

### `/bound` — Whitelist Binding

Bind / unbind / query game whitelist.

```
/bound                # View your bindings
/bound <player name>      # Bind whitelist
/bound remove <player name>  # Unbind
/bound remove --all   # Unbind all
```

- Player names may only contain letters, digits, and underscores, with a maximum length of 16 characters.
- The number of bindings is limited by `qq_bound_max_number`.

### `/help` — Help

View the list of available commands, or view detailed help for a specific command.

```
/help              # List all commands
/help <command name>    # View details for the specified command
```

### `/bot` — Bot Management

The bot management entry, integrating about info, version check, update, restart, and superuser management.

```
/bot about                    # View about info (version / update status / project links)
/bot check                    # Actively check for new versions
/bot update                   # Pull the latest code and auto-restart (requires admin)
/bot restart                  # Restart the bot (requires admin)
/bot superusers add <@user/ID>     # Add a superuser (requires admin)
/bot superusers remove <@user/ID>  # Remove a superuser (requires admin)
```

::: table title="/bot Subcommand Permissions" copy="all"
| Subcommand | Function | Permission |
|--------|------|------|
| `about` | About info (version / update status / project links) | All users |
| `check` | Actively check whether a new version is available | All users |
| `update` | Pull the latest code and auto-restart (based on git pull) | <Badge type="danger" text="Admin" /> |
| `restart` | Restart the bot through the watchdog | <Badge type="danger" text="Admin" /> |
| `superusers add/remove` | Add / remove superusers, written back to `.env` | <Badge type="danger" text="Admin" /> |
:::

Common examples:

```
/bot about                     # View about info
/bot check                     # Check for new versions
/bot superusers add @someone       # Add a superuser
/bot superusers remove 123456  # Remove a superuser
```

- `superusers` supports `@user` or a bare user ID.
- `update` depends on a git deployment (pulls the latest code with `git pull --ff-only`) and restarts only when new commits were actually pulled; when not started by Watchdog, it reports that automatic updates are unavailable.
- `restart` / `update` require the bot to be started by the Watchdog daemon (`Watchdog.py`); otherwise, it reports that it cannot be executed automatically.
- `superusers` changes take effect immediately, but framework-level permissions fully take effect only after a restart (consistent with the old `/config` behavior).

## Platform Prefixes

Commands respond to the same group format across platforms, distinguished by a platform prefix:

::: table title="Platform Prefixes" copy="all"
| Platform | Prefix |
|------|------|
| QQ client | `qq_client` |
| QQ guild | `qq_guild` |
| QQ API | `qq_api` |
| Telegram | `telegram` |
| Discord | `discord` |
| Kook | `kook` |
:::

Fill in `command_groups` / `message_groups` using the `"{platform}:{group-id}"` format.