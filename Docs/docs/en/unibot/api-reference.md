---
title: "REST API Reference"
date: 2026-08-21
description: "REST API reference for UniBot's WebUI backend: JWT authentication, login, server and player management, config read/write — all endpoints under the /api prefix with parameters and responses."
---

# REST API Reference

UniBot's WebUI backend provides a set of REST APIs for the frontend admin panel. All APIs are mounted under the bot's port with the `/api` path prefix.

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

## Log API

```
GET /api/logs?level=INFO&limit=100  # Fetch logs
```

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
`result`, `created_at` / `started_at` / `finished_at`, `retryable`, `log_count` (the detail endpoint additionally returns `logs`).

Task status changes are pushed in real time through the WebSocket `task` event.

## WebSocket Push

```
WS /api/ws
```

Pushes runtime status, log increments, server events, etc. in real time for the frontend dashboard to update live.

*For the complete API definitions, refer directly to the route files under the backend source `Scripts/Api/` directory.*
