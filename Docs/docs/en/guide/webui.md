# Admin Panel

**WebUI** is UniBot's built-in modern web admin panel, built on **Vue 3 + Vite + Pinia + reka-ui**, interacting with the backend through a REST API and WebSocket.

It provides **visual configuration, real-time monitoring, server / player management, log viewing**, and more, and is the primary entry point for daily use of UniBot. ==With WebUI, you'll basically never need to manually edit configuration files== — deployment and maintenance are done entirely in the browser.

## Features at a Glance

::: table title="WebUI Main Features" copy="all"
| View | Features |
|------|------|
| **::fluent-color:data-pie-24:: Dashboard** | Real-time running status, memory/CPU usage, online server count, bound player count; the "Quick Start" guide card at the top |
| **::fluent-color:clipboard-24:: Servers** | View the status of all connected servers and online players; enter the details page to execute commands remotely |
| **::fluent-color:people-24:: Player Management** | Manage whitelist bindings, associating platform users with game IDs |
| **::fluent-color:puzzle-piece-24:: Adapters** | View / install / enable / configure communication adapters for each platform (Minecraft, OneBot V11, etc.) |
| **::fluent-color:apps-list-24:: Plugin Management** | View the list of loaded NoneBot2 plugins and their enable/disable status |
| **::fluent-color:toolbox-24:: Extension Management** | Manage UniBot extensions: enable/disable, configure, switch rendering engines and templates, and access the extension marketplace |
| **::fluent-color:settings-24:: Config Center** | Visually edit `Config.toml` and `.env`, with Schema validation, grouped display, and source mode support |
| **::fluent-color:document-24:: Log Viewer** | Real-time scrolling view of runtime logs, with file switching and level filtering |
| **::fluent-color:person-24:: User Management** | Manage WebUI login accounts, roles, and permissions |
| **::fluent-color:person-key-24:: Personal Settings** | View the current account info, change your password |
| **::fluent-color:lock-closed-24:: Login Authentication** | JWT + password authentication (HttpOnly Cookie); first visit guides you through initializing the admin account |
:::

## Enable and Access

### Prerequisites

The WebUI dependencies must be installed first, and WebUI must be enabled in `Config.toml`:

```bash
# Install webui dependencies (required for both the install script and manual deployment)
cd UniBot
uv sync --extra webui --inexact
```

```toml
[webui]
enabled = true
```

::: warning
==WebUI cannot be enabled if the dependency installation above hasn't been run==, please make sure the dependencies are installed first.
:::

### Startup and Access

1. Start the bot: `uv run Watchdog.py`.
2. On the first start, the bot will **automatically download the WebUI static assets matching its own version from GitHub Releases** and mount them.
3. Open `http://<your-ip>:<PORT>/webui` in your browser (default `http://127.0.0.1:8000/webui`).

### Initialize the Admin

**Complete initialization on your first visit**: the page will guide you through creating an admin account (username + password). Once created, you can log in and enter the dashboard.

::: note
The admin account protects WebUI's management features. For multi-user collaboration, you can create more accounts in "User Management".
:::

## Page Details

### Dashboard

After logging in, you land on the dashboard by default, showing the bot's real-time running status:

- Top status bar: connection status, online server count, online player count, memory / CPU usage.
- **"Quick Start" guide card**: a progress checklist running through the entire deployment process; the three steps auto-detect their completion status:
  1. **Connect a chat platform** — completes automatically once an enabled chat platform adapter is detected;
  2. **Connect a Minecraft server** — completes automatically once a server is connected (an online server exists or a WS address is configured);
  3. **Add a superuser** — completes automatically once `SUPERUSERS` is non-empty.
  
  When all steps are complete, the card collapses automatically; it can also be collapsed manually (the state is remembered in browser local storage).
- Server overview: a quick overview of the online status of all connected servers.

#### Quick Start Guide Card

The "Quick Start" guide card is the **deployment progress checklist** at the top of the dashboard; the completion status of the following three steps is determined fully automatically:

::: steps

1. **Connect a chat platform**

   Completes automatically once a QQ / Telegram or other platform adapter is installed and enabled; click to jump to the adapter management page.

2. **Connect a Minecraft server**

   Completes automatically once a server is connected through the QueQiao plugin (an online server exists, or a WebSocket address is configured); click to view the QueQiao installation documentation.

3. **Add a superuser**

   Set an admin to use admin commands; click the "Token Authorization" button on the right to complete authorization quickly.

:::

Once all three steps are complete, the card collapses automatically. **This card is just a visual checklist of deployment progress**, mapping one-to-one to the steps of the deployment documentation:

| Guide Card Step | Corresponding Documentation Section |
|------|------|
| Connect a chat platform | [Quick Start · Step 3](/en/guide/quick-start.html#step-3-connect-chat-platforms) |
| Connect a Minecraft server | [Quick Start · Step 2](/en/guide/quick-start.html#step-2-install-and-configure-queqiao) |
| Add a superuser | [Quick Start · Step 4](/en/guide/quick-start.html#step-4-verify-startup) |

::: tip
The completion status of the guide card is detected automatically by WebUI (online adapter present / online server present / `SUPERUSERS` non-empty), ==no manual checking required==.
:::

##### Token Authorization

In the "Add a superuser" step of the guide card, click **Token Authorization**; the dialog will show the currently valid authentication token:

- Copy the token and send it in a **group chat on any platform**;
- The bot completes the authorization automatically: it adds the **current group** to the message groups and command groups (`message_groups` / `command_groups`), and sets the **sender** as a superuser (`SUPERUSERS`);
- The token is **one-time-use and auto-refreshing**: it refreshes immediately after a single use, and the old token is invalidated.

::: note Authorization without WebUI is also possible
Every time the bot starts, it prints the current token in the console (in the form `认证令牌：A1B2C3D4E5`), and sending it in a group chat on any platform completes the same authorization.

Afterwards, you can also add superusers manually in the [Config Center](#config-center) of WebUI.
:::

### Server Management

- **Server list**: view the connection status, type, and online status of all servers.
- **Server details**: view a single server's online players, server type, and status details, and **execute commands remotely** (send commands to the server console).

### Player Management

Manage blacklist / whitelist bindings: associate platform users (such as QQ numbers) with game IDs, with support for searching and adding / unbinding.

### Adapter Management

- View installed platform adapters (Minecraft, OneBot V11, etc.).
- Install / enable / disable / configure adapters.
- Core adapters (such as Minecraft) are marked as **protected** and cannot be operated on.

::: note
When you install a platform adapter through WebUI, UniBot automatically handles dependency installation and registration. See [Connect Chat Platforms](/en/adapter/connect-chat-platforms.html).
:::

### Plugin Management

View the list of loaded NoneBot2 plugins and their enable/disable status. All plugins come from the official plugin registry; after installation, refer to the plugin's GitHub documentation and configure the parameters yourself in `.env`.

### Extension Management

The management entry for the UniBot extension system (requires admin permissions):

- View all installed extensions and their status (enabled / disabled / isolated).
- Adjust extension business configuration (forms are generated dynamically based on the model's JSON Schema).
- Switch rendering engines and templates (template switching takes effect immediately).
- Access the **extension marketplace** to search and one-click install / upgrade / uninstall extensions.

See the "WebUI Management" section in [Extension System](/en/unibot/extension-system.html).

### Config Center

- **`Config.toml`**: config items displayed in groups, with Schema validation; save after editing and (as needed) restart.
- **`.env`**: environment variables displayed in groups (including **bot card** editing for bot list fields such as `QQ_BOTS`, `TELEGRAM_BOTS`, etc.); saving changes requires **restarting the bot to take effect**.
- **`Messages.toml`**: edit message template text.
- **Source mode** is also available, for editing TOML / env sources directly.

::: warning
==Changes to `.env` require a bot restart to take effect after saving==; the restart is handled by `Watchdog.py`, with no manual intervention needed.
:::

### Log Viewer

View runtime logs in real time via WebSocket scrolling, with support for selecting the log file and filtering by level, making troubleshooting easier.

### User Management

Manage WebUI login accounts: create / edit / disable users, assign role permissions, reset passwords. (Visible only to admins)

### Personal Settings

View the current account info and change your own password.

## Authentication and Security

- WebUI uses **JWT + password authentication**, with tokens stored in **HttpOnly Cookies** (`unibot_access_token` / `unibot_refresh_token`), which front-end JS cannot read, reducing XSS risk.
- When the `access_token` expires, the refresh token is used to renew automatically, with no need to log in again.
- Unauthenticated users can only access the login page; the **Config Center** and **User Management** pages are accessible only to admins.
- It is recommended to enable HTTPS for WebUI in production via a reverse proxy (Nginx / Caddy, etc.).

## FAQ

### WebUI Shows 404 / Fails to Load

1. Confirm `[webui] enabled = true` and that `uv sync --extra webui --inexact` has been run.
2. Confirm the access path is `/webui` and the port is correct (default `8000`).
3. Check the bot logs and confirm whether the WebUI static assets were downloaded and mounted successfully.

### Login Says Wrong Password / Forgot the Admin Password

- Confirm the account password set during admin initialization.
- If forgotten, reset it in the server-side data (see the relevant APIs in [User Management](/en/unibot/api-reference.html)).

### Config Changes in WebUI Not Taking Effect

- Changes to `Config.toml` generally require a restart; `Watchdog.py` handles it automatically on save.
- Changes to `.env` **must restart the bot to take effect** after saving; if prompted to restart, follow the on-page instructions.

### How to Protect WebUI from Others

- Bind the bot to an internal address, or protect the `/webui` path with a reverse proxy + HTTPS + access control.
- Manage WebUI accounts carefully and promptly disable accounts you no longer need.

## More

- **API Documentation**: the WebUI backend REST API reference is in [API Documentation](/en/unibot/api-reference.html).
- **Deployment flow**: for a from-scratch deployment, see [Quick Start](/en/guide/quick-start.html).
- **Configuration Documentation**: all configuration items of `.env` and `Config.toml` are in [Configuration Documentation](/en/unibot/configuration.html).