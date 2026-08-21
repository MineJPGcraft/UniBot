---
home: true
pageLayout: home
config:
  -
    type: doc-hero
    hero:
      name: Minecraft UniBot
      tagline: 跨平台 · 多服互联 · 即插即用
      text: 让 Minecraft 与你的聊天世界无缝相连
      image: /icon.svg
      actions:
        -
          theme: brand
          text: 了解项目
          link: /guide/features.html
        -
          theme: alt
          text: 快速开始
          link: /guide/quick-start.html
  -
    type: features
    features:
      -
        title: 真正的跨平台
        icon: fluent-color:globe-24
        details: 不止 QQ，还支持 Telegram、Discord、Kook、QQ 频道等，一套指令全平台通用。
      -
        title: 多服互联
        icon: fluent-color:link-24
        details: 同时连接多台 Minecraft 服务器，消息互通，跨服聊天零延迟。
      -
        title: 全服务端兼容
        icon: fluent-color:arrow-sync-24
        details: 支持 Fabric、Forge、Spigot、Paper 等主流服务端，即插即用，无需额外适配。
      -
        title: 扩展系统
        icon: fluent-color:toolbox-24
        details: 指令、服务、渲染引擎、模板与资源五类扩展，即插即用，失败自动隔离。
      -
        title: WebUI 管理面板
        icon: fluent-color:laptop-24
        details: 现代化管理界面，可视化配置、实时监控、日志查看，开箱即用。
        link: /guide/webui.html
      -
        title: NoneBot2 生态
        icon: fluent-color:bot-24
        details: 基于 NoneBot2 构建，无缝接入 NB 插件商店，社区现成插件开箱即用。
      -
        title: 白名单管理
        icon: fluent-color:lock-closed-24
        details: 完善的平台账号与游戏 ID 绑定系统，支持多服白名单同步。
      -
        title: 图片渲染模式
        icon: fluent-color:paint-brush-24
        details: 渲染引擎与模板自由组合，将指令输出渲染为精美图片，支持自定义背景。
  -
    type: custom
---

这是 **Minecraft UniBot** 项目的官方文档。本项目由多个子项目共同构成，目标是打造一套跨平台、多服互联的 Minecraft 机器人生态。

## ::fluent-color:chart-multiple-24:: 机器状态

<ClientOnly>
  <MachineStats />
</ClientOnly>

<script setup>
import MachineStats from './.vuepress/components/MachineStats.vue'
</script>

## ::fluent-color:book-24:: 项目组成

| 子项目 | 说明 | 技术栈 |
|--------|------|--------|
| [UniBot](/unibot/) | 主机器人框架，负责消息收发、指令处理与 WebUI 管理 | NoneBot2 / Python |
| [MC 适配器](/adapter/) | NoneBot 的 Minecraft 协议适配器，为 UniBot 提供 MC 通信能力 | NoneBot Adapter |

> [!TIP]
> 本文档中的「鹊桥」指 [17TheWord / QueQiao](https://github.com/17TheWord/QueQiao) 官方维护的第三方通信协议，支持 MCDReforged、Spigot、Paper、Fabric、Forge、NeoForge、Vanilla、Folia、Velocity 等多种服务端。UniBot 通过 [MC 适配器](/adapter/) 与鹊桥互通。

## ::fluent-color:send-24:: 快速导航

- [开始使用](/guide/quick-start.html) — 从零开始部署你的 UniBot
- [WebUI 管理面板](/guide/webui.html) — 可视化配置、实时监控、日志查看
- [配置说明](/unibot/configuration.html) — 全部配置项详解
- [指令手册](/guide/command-reference.html) — 全部内置指令一览
- [功能特性](/guide/features.html) — 群服互通、图片渲染、扩展系统等
- [扩展系统](/unibot/extension-system.html) — 扩展类型、渲染体系与可视化管理
- [架构设计](/unibot/architecture.html) — 深入了解项目架构
- [MC 适配器](/adapter/) — 鹊桥协议与服务器端接入方式
