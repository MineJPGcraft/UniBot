---
title: REST API 参考
date: 2026-08-04
description: UniBot WebUI 后端 REST API 参考：JWT 认证、登录鉴权、服务器与玩家管理、配置读写等接口的路径、参数与响应说明，路径前缀 /api。
---

# REST API 参考

UniBot 的 WebUI 后端提供一组 REST API，供前端管理面板调用。所有 API 均挂载在机器人的端口下，路径前缀为 `/api`。

## 认证方式

采用 **JWT + HttpOnly Cookie** 认证：

- 登录成功后，后端通过 `Set-Cookie` 下发 `access_token`（2 小时）和 `refresh_token`（7 天）。
- 前端请求需要携带 Cookie（`credentials: 'include'`）。
- 也可以用 `Authorization: Bearer <token>` 头来传递。

==令牌存放在 HttpOnly Cookie 中，前端 JS 无法读取，可有效降低 XSS 风险。==

## API 概览

::: table title="API 概览" copy="all"
| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth` | 登录、刷新、登出 |
| 配置 | `/api/config` | 读取/修改配置 |
| 扩展 | `/api/extensions` | 扩展列表、启停、配置、渲染设置 |
| 玩家 | `/api/players` | 白名单绑定管理 |
| 服务器 | `/api/servers` | 服务器状态与指令 |
| 插件 | `/api/plugins` | 插件列表与状态 |
| 日志 | `/api/logs` | 日志查看 |
| 状态 | `/api/status` | 运行状态监控 |
| 统计 | `/api/statistics` | 消息统计与活跃群聊 |
| 用户 | `/api/users` | 用户管理 |
| WebSocket | `/api/ws` | 实时推送 |
:::

## 认证接口

### 登录

```
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

响应会设置 JWT Cookie，前端据此保持登录态。

### 刷新令牌

```
POST /api/auth/refresh
```

### 登出

```
POST /api/auth/logout
```

## 配置接口

### 读取配置

```
GET /api/config
```

返回当前配置（按分组展示）。

### 修改配置

```
PUT /api/config
Content-Type: application/json

{
  "section": "webui",
  "key": "enabled",
  "value": true
}
```

修改后需重启机器人才生效（由 Watchdog 处理）。

## 状态接口

```
GET /api/status
```

返回机器人运行状态，包括内存占用、在线服务器数、绑定玩家数等。

## 服务器接口

```
GET /api/servers                    # 所有服务器状态
GET /api/servers/{name}             # 指定服务器详情
POST /api/servers/{name}/command    # 远程执行指令
```

## 统计接口

由「数据统计」插件在后台自动收集，数据持久化于 `Data/Statistics.json`。

### 获取统计数据

```
GET /api/statistics?days=30         # days 为趋势天数（1-90，默认 30）
```

返回总览摘要、按天趋势、活跃群聊排行、平台分布以及当前已连接的机器人列表。

### 清空统计数据

```
POST /api/statistics/reset
```

清空全部统计数据并立即落盘，需要 <Badge type="danger" text="管理员权限" />。

## 玩家接口

```
GET /api/players                    # 玩家列表
PUT /api/players/{id}               # 修改绑定
DELETE /api/players/{id}            # 删除绑定
```

## 扩展接口

扩展管理接口挂载于 `/api/extensions`。

::: warning
**修改配置、启停、卸载、安装以及切换渲染引擎 / 模板** 均要求 <Badge type="danger" text="管理员权限" />；列表与详情接口至少要求已认证用户。
:::

### 扩展列表

```
GET /api/extensions
```

返回已安装扩展列表（类型、版本、依赖、启停状态）。

### 扩展详情

```
GET /api/extensions/items/{id}
```

返回指定扩展的详情与配置 Schema。

### 启用 / 禁用

```
POST /api/extensions/{id}/enable
POST /api/extensions/{id}/disable
```

持久化启停意图，重启后生效。启用接口在依赖仍被禁用、缺失或版本不兼容时拒绝写入，并返回阻塞依赖及原因；禁用成功后，其依赖方在下一次加载时显示为 `blocked`。

### 扩展配置

```
GET  /api/extensions/{id}/config
PATCH /api/extensions/{id}/config
```

读取与更新扩展配置。配置更新会经过扩展模型校验，失败时返回字段级错误且不修改原配置。

### 渲染引擎管理

```
GET  /api/extensions/renderers
POST /api/extensions/renderers/switch
```

查看可用渲染引擎（含当前选中）并切换。渲染引擎切换重启后生效。

### 模板管理

```
GET  /api/extensions/templates
POST /api/extensions/templates/switch
```

查看可用模板扩展并切换，模板切换即时生效。

### 资源扩展

```
GET /api/extensions/resources
```

返回可用资源扩展及资源状态。资源扩展不支持配置。

## 日志接口

```
GET /api/logs?level=INFO&limit=100  # 获取日志
```

## WebSocket 推送

```
WS /api/ws
```

实时推送运行状态、日志增量、服务器事件等，供前端仪表盘实时更新。

*如需完整的接口定义，可直接查阅后端源码 `Scripts/Api/` 目录下的各路由文件。*