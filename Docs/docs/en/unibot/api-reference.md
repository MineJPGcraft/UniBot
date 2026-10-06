---
title: "REST API Reference"
date: 2026-08-21
description: "REST API reference for UniBot's WebUI backend: JWT authentication, login, server and player management, config read/write — mounted under /webui with the /api route prefix, with parameters and responses."
---

# REST API Reference

UniBot's WebUI backend provides a set of REST APIs for the frontend admin panel. The entire API router is mounted under the **`/webui`** prefix, and each module adds `/api/<module>` as its route prefix, so the **actual request path is `/webui/api/<module>/...`**. Below, each endpoint is written as `/api/...` for brevity; append the `/webui` mount prefix when calling it for real.

## Authentication

Authentication uses **JWT + HttpOnly Cookie**:

- After a successful login, the backend issues `access_token` (2 hours) and `refresh_token` (7 days) via `Set-Cookie`.
- Frontend requests must carry the Cookie (`credentials: 'include'`).
- You can also pass the `Authorization: Bearer <token>` header instead.

==Tokens are stored in HttpOnly Cookies that frontend JS cannot read, effectively reducing XSS risk.==

## API Overview

::: table title="API Overview" copy="all"
| Module | Route Prefix | Description |
|------|----------|------|
| Auth | `/api/auth` | Login, refresh, logout |
| Config | `/api/config` | Read / modify configuration |
| Extensions | `/api/extensions` | Extension list, enable/disable, config, render settings |
| Players | `/api/players` | Whitelist binding management |
| Servers | `/api/servers` | Server status and commands |
| Plugins | `/api/plugins` | Plugin list and status |
| Logs | `/api/logs` | Log viewing |
| Status | `/api/status` | Runtime status monitoring |
| Users | `/api/users` | User management |
| Tasks | `/api/tasks` | Background Task Center (list, detail, cancel, retry, dependency sync) |
| WebSocket | `/api/ws` | Real-time push |
:::

## Auth APIs

### Login

```
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

The response sets the JWT Cookie, which the frontend uses to keep the login state.

### Refresh Token

```
POST /api/auth/refresh
```

### Logout

```
POST /api/auth/logout
```

## Config APIs

### Read Config

```
GET /api/config
```

Returns the current configuration (grouped).

### Modify Config

```
PUT /api/config
Content-Type: application/json

{
  "section": "webui",
  "key": "enabled",
  "value": true
}
```

A bot restart is required for the change to take effect (handled by the Watchdog).

### Read Message Texts

```
GET /api/config/messages?language=zh
```

Returns a nested tree grouped by the **namespace** of translation keys. Each namespace node carries `name` / `path` / `label` / `count` (messages in the subtree) / `modified_count` / `children` / `items`; each leaf message item carries `key` / `value` (effective value) / `base_value` (default translation) / `placeholders` / `is_list` / `modified`.

```jsonc
{
  "language": "zh",
  "tree": [
    {
      "name": "core", "path": "core", "label": "Core texts",
      "count": 123, "modified_count": 0,
      "children": [
        { "name": "events", "path": "core.events", "label": "Event broadcasts", "count": 26,
          "items": [{ "key": "core.events.player_join", "value": "玩家 {player} 加入了游戏。", "...": "..." }] }
      ],
      "items": []
    }
  ],
  "total_count": 123,
  "modified_count": 0
}
```

System keys (system commands, built-in extension/plugin names, `api.*` UI text) are protected and not returned.

### Save Message Overrides

```
PATCH /api/config/messages
Content-Type: application/json

{
  "language": "zh",
  "overrides": { "core.events.player_join": "玩家 {player} 上线啦！" }
}
```

`overrides` is a `key → new value` map; protected keys and entries equal to the default translation are pruned, then written to `Config/Messages.{zh,en}.toml` (only changed keys are kept) and hot-applied immediately.

### Read Raw Sources

```
GET  /api/config/raw                # Config.toml source
GET  /api/config/env                # .env source (source mode)
```

## Status API

```
GET /api/status
```

Returns the bot's runtime status, including memory usage, online server count, bound player count, etc.

## Server APIs

```
GET /api/servers                    # Status of all servers
GET /api/servers/{name}             # Details of a specific server
POST /api/servers/{name}/command    # Execute a command remotely
```

## Player APIs

```
GET /api/players                    # Player list
PUT /api/players/{id}               # Modify a binding
DELETE /api/players/{id}            # Delete a binding
```

## Extension APIs

Extension management APIs are mounted at `/api/extensions`.

::: warning
**Modifying config, enable/disable, uninstall, install, and switching rendering engines / templates** all require <Badge type="danger" text="Admin permission" />; the list and detail APIs require at least an authenticated user.
:::

### Extension List

```
GET /api/extensions
```

Returns the list of installed extensions (type, version, dependencies, enable/disable status).

### Extension Details

```
GET /api/extensions/items/{id}
```

Returns the details and config Schema of a specific extension.

### Enable / Disable

```
POST /api/extensions/{id}/enable
POST /api/extensions/{id}/disable
```

Persists the enable/disable intent, taking effect after restart. The enable API rejects the write when dependencies are still disabled, missing, or version-incompatible, and returns the blocking dependencies with reasons; after a successful disable, dependents show as `blocked` on the next load.

### Extension Config

```
GET   /api/extensions/config-items     # every extension declaring config options (incl. no-code template packs)
GET   /api/extensions/{id}/config
PATCH /api/extensions/{id}/config
```

Read and update the extension config. `config-items` lets the Config Center fetch the schema and current values of all editable extensions at once. Config updates are validated against the extension model; on failure, field-level errors are returned and the original config is left unchanged. Secret fields are returned as the `<configured>` placeholder; sending that placeholder back keeps the current value unchanged.

### Rendering Engine Management

```
GET  /api/extensions/renderers
POST /api/extensions/renderers/switch
```

View available rendering engines (including the currently selected one) and switch between them. Rendering engine switches take effect after restart.

### Template Management

```
GET  /api/extensions/templates
POST /api/extensions/templates/switch
```

View available template extensions and switch between them. Template switches take effect immediately.

### Resource Extensions

```
GET /api/extensions/resources
```

Returns available resource extensions and their status. Resource extensions do not support configuration.

### Marketplace Install and Version Switching

```
POST /api/extensions/market/install
GET  /api/extensions/market/{id}/releases
```

`market/install` submits a background installation task. Request body:

| Field | Description |
|-------|-------------|
| `id` | Extension id |
| `version` | Optional; **leave it out** to auto-select the newest release compatible with the current UniBot version, or pass an explicit version to install it (useful for rolling back) |

When auto-selecting: the latest release is used if compatible; if the latest is incompatible but a compatible older release exists, it falls back and logs the reason; if no release is compatible at all, the request fails with "this extension does not support the current core version".

`market/{id}/releases` returns every available release of that extension:

```json
{
  "unibot_version": "1.0.3",
  "releases": [{ "version": "1.0.2", "unibot_version": ">= 1.0.2", "compatible": true, "installed": false }]
}
```

## Log API

```
GET /api/logs                 # List log files
GET /api/logs/{name}?lines=N  # Fetch the last N lines (default 2000, max 10000)
```

To avoid loading an entire file into memory and blocking the event loop, the content endpoint returns
only the tail by default; use `lines` to control how many trailing lines are returned.

## Task APIs

The background Task Center APIs are mounted at `/api/tasks`, covering dependency sync, market extension installs/uninstalls, extension hot reloads, Studio launches, plugin market operations and version updates.

::: warning
List and detail endpoints require an authenticated user; **cancel, retry and manual dependency sync** require <Badge type="danger" text="Admin" /> privileges.
:::

```
GET  /api/tasks                     # Task list + status summary
GET  /api/tasks/{id}                # Task detail (including logs)
POST /api/tasks/{id}/cancel         # Cancel a task
POST /api/tasks/{id}/retry          # Retry a task
POST /api/tasks/dependency-sync     # Trigger dependency sync manually
```

Task snapshot fields: `id`, `kind`, `title_params`, `status` (`pending` / `running` / `succeeded` / `failed` / `cancelled`),
`message_key` + `message_params` (stage description, translated by the frontend into the UI language), `progress`, `error`,
`result`, `created_at` / `started_at` / `finished_at`, `retryable`, `cancel_requested` (cancellation requested but not yet
finalized), `log_count` (the detail endpoint additionally returns `logs`).

Task status changes are pushed in real time through the WebSocket `task` event.

## WebSocket Push

```
WS /api/ws
```

Pushes runtime status, log increments, server events, etc. in real time for the frontend dashboard to update live.

Authentication only accepts same-origin HttpOnly cookies (automatically sent by browser WebSockets); **tokens in the URL
query are not accepted** (URLs leak into browser history, proxies and access logs).

*For the complete API definitions, refer directly to the route files under the backend source `Core/Web/` directory.*
