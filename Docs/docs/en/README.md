---
home: true
pageLayout: home
config:
  -
    type: doc-hero
    hero:
      name: Minecraft UniBot
      tagline: Cross-platform · Multi-server · Plug-and-Play
      text: Seamlessly connect Minecraft with your chat world
      image: /icon.svg
      actions:
        -
          theme: brand
          text: Learn About the Project
          link: /en/guide/features.html
        -
          theme: alt
          text: Quick Start
          link: /en/guide/quick-start.html
  -
    type: features
    features:
      -
        title: Truly Cross-Platform
        icon: fluent-color:globe-24
        details: Not just QQ — also Telegram, Discord, Kook, QQ Guilds and more. One command set that works across every platform.
      -
        title: Multi-Server Interconnection
        icon: fluent-color:link-24
        details: Connect multiple Minecraft servers simultaneously with inter-server messaging and zero-latency cross-server chat.
      -
        title: Compatible with All Server Types
        icon: fluent-color:arrow-sync-24
        details: Supports Fabric, Forge, Spigot, Paper and other mainstream server platforms — plug-and-play, no extra adaptation needed.
      -
        title: Extension System
        icon: fluent-color:toolbox-24
        details: Five extension types — commands, services, rendering engines, templates and resources — plug-and-play with automatic failure isolation.
      -
        title: WebUI Admin Panel
        icon: fluent-color:laptop-24
        details: A modern management interface with visual configuration, real-time monitoring and log viewing, out of the box.
        link: /en/guide/webui.html
      -
        title: NoneBot2 Ecosystem
        icon: fluent-color:bot-24
        details: Built on NoneBot2, seamlessly compatible with the NB plugin store — community plugins work out of the box.
      -
        title: Whitelist Management
        icon: fluent-color:lock-closed-24
        details: A complete platform-account to game-ID binding system with multi-server whitelist synchronization.
      -
        title: Image Rendering Mode
        icon: fluent-color:paint-brush-24
        details: Freely combine rendering engines and templates to turn command output into beautiful images, with custom backgrounds.
  -
    type: custom
---

This is the official documentation for the **Minecraft UniBot** project. The project is made up of several sub-projects, all aimed at building a cross-platform, multi-server Minecraft bot ecosystem.

## ::fluent-color:chart-multiple-24:: Bot Status

<ClientOnly>
  <MachineStats
    online-machine-label="Online Machines"
    total-machine-label="Total Machines"
    connected-bot-label="Connected Bots"
    sent-total-label="Messages Sent"
    received-total-label="Messages Received"
    error-label="Failed to load statistics"
  />
</ClientOnly>

<script setup>
import MachineStats from '../.vuepress/components/MachineStats.vue'
</script>

## ::fluent-color:book-24:: Project Components

| Sub-project | Description | Tech Stack |
|-------------|-------------|------------|
| [UniBot](/en/unibot/) | The main bot framework, responsible for message sending/receiving, command handling and WebUI management | NoneBot2 / Python |
| [MC Adapter](/en/adapter/) | The Minecraft protocol adapter for NoneBot, providing UniBot with MC communication capabilities | NoneBot Adapter |

> [!TIP]
> In this documentation, "QueQiao" (鹊桥) refers to the third-party communication protocol maintained by [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao), which supports MCDReforged, Spigot, Paper, Fabric, Forge, NeoForge, Vanilla, Folia, Velocity and other server platforms. UniBot communicates with QueQiao through the [MC Adapter](/en/adapter/).

## ::fluent-color:send-24:: Quick Navigation

- [Get Started](/en/guide/quick-start.html) — deploy your UniBot from scratch
- [WebUI Admin Panel](/en/guide/webui.html) — visual configuration, real-time monitoring, log viewing
- [Configuration Guide](/en/guide/configuration.html) — detailed reference for all configuration options
- [Command Reference](/en/guide/command-reference.html) — all built-in commands at a glance
- [Features](/en/guide/features.html) — group-server interop, image rendering, extension system and more
- [Extension System](/en/unibot/extension-system.html) — extension types, rendering system and visual management
- [Architecture](/en/unibot/architecture.html) — dive into the project architecture
- [MC Adapter](/en/adapter/) — QueQiao protocol and server-side integration
