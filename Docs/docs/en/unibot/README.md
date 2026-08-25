---
title: "UniBot Core"
description: "UniBot core documentation: a Minecraft cross-server bridge bot built on NoneBot2, compatible with the NB Plugin Store — architecture, extension system, REST API and development guides."
---

# UniBot

**UniBot** is the core bot of Minecraft UniBot, built on the [NoneBot2](https://nonebot.dev/) framework, responsible for communicating with chat platforms and multiple Minecraft servers. UniBot is fully compatible with the NoneBot2 ecosystem, can seamlessly integrate with the [NB Plugin Store](https://registry.nonebot.dev/), and can directly use community-ready plugins.

## Quick Navigation

<LinkCard title="Configuration Guide" href="/en/guide/configuration.html" icon="fluent-color:settings-24">

  All configuration items including `.env` and `Config.toml`

</LinkCard>

<LinkCard title="Extension System" href="/en/unibot/extension-system.html" icon="fluent-color:puzzle-piece-24">

  Extension types, manifest, states, and rendering system

</LinkCard>

<LinkCard title="Architecture" href="/en/unibot/architecture.html" icon="fluent-color:apps-24">

  Dive into the project structure

</LinkCard>

<LinkCard title="REST API" href="/en/unibot/api-reference.html" icon="fluent-color:code-24">

  WebUI backend API reference

</LinkCard>

<LinkCard title="Developing Extensions" href="/en/unibot/developing-extensions.html" icon="fluent-color:wrench-screwdriver-24">

  Write your own UniBot extensions

</LinkCard>

<LinkCard title="Publish to Marketplace" href="/en/unibot/marketplace.html" icon="fluent-color:building-store-24">

  Publish your extension to the extension marketplace

</LinkCard>

## Tech Stack

::: table title="Tech Stack Overview" copy="all"
| Category | Technology |
|------|------|
| Framework | NoneBot2 (FastAPI driven) |
| Command Parsing | Alconna |
| Session Info | uninfo |
| Data Validation | Pydantic |
| HTTP Client | httpx |
| Image Rendering | Jinja2 (template) + html2pic / Playwright (engine) |
| Authentication | JWT + bcrypt |
| Frontend | Vue 3 + Vite + Pinia |
:::

## Core Capabilities

- **Cross-platform Messaging**: one set of command logic, universal across all platforms.
- **Multi-server Interconnect**: connect to multiple servers simultaneously, forwarding messages between them.
- **Extension System**: five types of extensions — commands, services, rendering engines, templates, and resources — enabled/disabled on demand with failure isolation.
- **WebUI Admin Panel**: visual configuration, monitoring, logs, and extension management.
- **Image Rendering**: render command output as polished images, with freely combinable templates and engines.
- **Whitelist Management**: bind platform accounts to game IDs.
- **NoneBot2 Ecosystem**: seamless integration with the NB Plugin Store; community plugins are plug-and-play.

## Directory Structure

```file-tree
UniBot/
├── Bot.py                 # Bot entry point
├── Watchdog.py            # Watchdog process (auto-restart)
├── Config.toml            # Bot configuration
├── Config/
│   ├── Extensions.toml    # Extension toggle
│   ├── Extensions/        # Extension config (one file per extension)
│   └── Messages.toml      # Message text
├── Data/                  # Data persistence (JSON)
│   ├── Extension/         # Extension management state
│   └── Exs/               # Extension business data
├── Logs/                  # Runtime logs
├── Extensions/            # Extension packages (local / marketplace)
├── Plugins/               # NoneBot plugins (command modules)
│   ├── Commands/          # Built-in commands
│   └── Events.py          # Event processing hub
├── Scripts/               # Core scripts
│   ├── Extensions/        # Extension system framework
│   ├── Managers/          # Managers (data, servers, plugins, etc.)
│   ├── Api/               # REST API routes
│   ├── Config.py          # Config models
│   ├── Network.py         # Network utilities
│   └── ...
└── WebUi/                 # Vue 3 admin panel frontend
```

## Startup

UniBot has two entry points:

- **`Bot.py`**: runs the bot process directly.
- **`Watchdog.py`**: a watchdog process that monitors abnormal bot exits and restarts automatically, while also handling WebUI restart requests and dependency sync.

==We recommend launching with `Watchdog.py`==:

```bash
uv run Watchdog.py
```
