# Guide

Welcome to **Minecraft UniBot**. This guide serves as the **user manual**, helping you install the bot and get started quickly. For deeper configuration, jump to the [Configuration Documentation](/en/unibot/configuration.html).

==If you're a first-time user, start with the "Quick Start"==, follow the steps to complete deployment; consult the other pages as needed.

## Where to Start

:::: card-grid

::: card title="Quick Start" icon="fluent-color:book-open-24"
New here? Start from this page and complete a minimal deployment step by step.

→ [Go to Quick Start](/en/guide/quick-start.html)
:::

::: card title="Command Reference" icon="fluent-color:book-24"
All built-in commands and their usage, checkable at a glance.

→ [Go to Command Reference](/en/guide/command-reference.html)
:::

::: card title="Features" icon="fluent-color:bot-sparkle-24"
All capabilities including group-server interop, image rendering, WebUI, and the extension system.

→ [View Features](/en/guide/features.html)
:::

::: card title="WebUI Admin Panel" icon="fluent-color:board-24"
Visual configuration, real-time monitoring, server / player management, and log viewing.

→ [Learn about WebUI](/en/guide/webui.html)
:::

::: card title="Architecture Design" icon="fluent-color:apps-24"
Understand the overall architecture and how components communicate with each other.

→ [View Architecture Design](/en/unibot/architecture.html)
:::

::: card title="Extension System" icon="fluent-color:puzzle-piece-24"
Learn about the extension mechanism and combine bot capabilities like building blocks.

→ [View Extension System](/en/unibot/extension-system.html)
:::

::: card title="Configuration Documentation" icon="fluent-color:settings-24"
Need to dig deeper into configuration? All configuration items are covered here.

→ [View Configuration Documentation](/en/unibot/configuration.html)
:::

::::

## Documentation Navigation

::: table title="Documentation Navigation" copy="all"
| Section | Content | Target Audience |
|------|------|--------|
| [Quick Start](/en/guide/quick-start.html) | Complete deployment in five steps | First-time users |
| [Command Reference](/en/guide/command-reference.html) | All built-in commands and usage | All users |
| [Features](/en/guide/features.html) | Group-server interop, image rendering, WebUI, extension system and more | Users who want to know all capabilities |
| [WebUI Admin Panel](/en/guide/webui.html) | WebUI page functions, how to enable it, and FAQ | Users of WebUI |
:::

> ::fluent-color:link-24:: **Configuration Documentation**: detailed reference for all configuration items such as `.env` and `Config.toml`, see [UniBot Configuration Documentation](/en/unibot/configuration.html).

## Project Components

This project consists of multiple sub-projects, each responsible for one part:

::: table title="Project Components" copy="all"
| Sub-Project | Role | Documentation |
|--------|------|------|
| [UniBot](/en/unibot/) | Core bot, responsible for communicating with chat platforms and multiple servers | [Architecture Design](/en/unibot/architecture.html) |
| [MC Adapter](/en/adapter/) | NoneBot's MC protocol adapter, the communication bridge | [Adapter Documentation](/en/adapter/) |
:::

> ::fluent-color:pin-24:: **About QueQiao**: QueQiao is a third-party communication protocol officially maintained by [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao), supporting multiple server platforms such as MCDReforged, Spigot, Paper, Fabric, and Forge. UniBot interconnects with QueQiao through the [MC Adapter](/en/adapter/).
