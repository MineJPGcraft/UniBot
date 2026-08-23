# Quick Start

Welcome to **Minecraft UniBot**. This page walks you through the complete deployment flow from scratch to a working bot; the whole process takes about *==10 minutes==*.

## Terminology

Before you begin, let's clarify the following terms to avoid ambiguity later:

::: table title="Terminology" copy="all"
| Term | Meaning |
|------|------|
| **Core / Implementation** | Refers to the `UniBot` project itself, a NoneBot2 server that actually implements the bot's functionality |
| **Bot** | QQ bot, Telegram Bot, etc., referring to the bot accounts created on each platform |
| **Bot protocol client** | Some bots (such as QQ) require a forwarding service to connect to the core; that forwarding service is the protocol client. Some platforms don't need this step |
:::

## Deployment Overview

::: steps

1. **Install the bot itself**

   Install and start UniBot, see [Step 1](#step-1-install-unibot).

2. **Install and configure the QueQiao plugin on the server**

   Install the QueQiao plugin on each Minecraft server, see [Step 2](#step-2-install-and-configure-queqiao).

3. **Connect chat platforms**

   Install and configure the adapter for the corresponding platform, see [Step 3](#step-3-connect-chat-platforms).

4. **Complete authorization and verify**

   Complete authorization through the Quick Start guide card in WebUI, see [Step 4](#step-4-verify-startup).

:::

If you want to first understand the overall architecture and how the components communicate, refer to [Architecture Overview](/en/unibot/architecture.html).

## Prerequisites

::: table title="Prerequisites" copy="all"
| Component | Requirement |
|------|------|
| Python | 3.11+ |
| Package manager | [UV](https://docs.astral.sh/uv/) (recommended) or pip |
| Minecraft server | Fabric / Forge / Spigot / Paper / MCDR, etc., with the QueQiao plugin already installed |
| Chat bot account | QQ bot, Telegram Bot, etc. |
:::

## Step 1: Install UniBot

### Script Installation (Recommended)

Download the one-click installation script for your platform from the [Releases page](https://github.com/MineJPGcraft/UniBot/releases):

::: table title="One-Click Installation Script" copy="all"
| Platform | Script |
|------|------|
| **Windows** | `Install.bat`, just double-click to run; it automatically installs uv, clones the repository, configures WebUI, and syncs dependencies |
| **Linux / macOS** | `Install.sh`, first run `chmod +x Install.sh`, then run `./Install.sh` |
:::

The script will automatically: detect and install UV, pull the repository for the corresponding version, ask whether to enable WebUI, and run `uv sync` to sync dependencies.

::: note
After installation, the script will generate a `Start.sh` or `Start.bat` in the `UniBot` directory; you only need to run it to start the core.

To start manually, just run `uv run Watchdog.py` in the root directory.
:::

**==With WebUI, you'll basically never need to manually edit the configuration afterward.==** After starting, open `http://<ip>:<port>/` in your browser (default `http://127.0.0.1:8000/webui`). On first visit, follow the prompts to initialize the admin account, then you can configure chat platforms, manage servers, and view logs in WebUI.

Just follow the guide to complete the entire configuration flow quickly — **no need to manually edit `.env` or `Config.toml`, and no need to consult the documentation.**

::: note
A full introduction to WebUI's features (detailed page explanations, Config Center, log viewing, token authorization, etc.) is available in the [WebUI Admin Panel](/en/guide/webui.html).
:::

### Manual Installation (Optional)

```bash
# Clone the project and create a virtual environment
git clone https://github.com/MineJPGcraft/UniBot
cd UniBot

# Install the core and WebUI dependencies
uv sync --extra webui

# Start the bot
uv run Watchdog.py
```

~~You can also install with pip + venv~~, see the [Configuration Guide](/en/guide/configuration.html) for the exact commands, but uv is recommended for management.

### Docker Installation
After installing Docker, run the following in a terminal
```bash
docker run -d -p 8000:8000 ghcr.io/minejpgcraft/unibot:latest
```
UniBot will start running in the background

### Docker Compose Installation
After installing Docker and Compose, run
```bash
git clone https://github.com/MineJPGcraft/UniBot
cd UniBot
docker compose up -d
```

## Step 2: Install and Configure QueQiao

Every **Minecraft server** needs to have the **==QueQiao plugin/mod==** installed to connect to the core.

After installation, you also need to configure it so the server and the bot can establish a connection and communicate normally. For detailed installation methods and plugin download links, refer to the [Minecraft Adapter](/en/adapter/), and choose the installation mode that fits your needs.

## Step 3: Connect Chat Platforms

In addition, you need to install and configure the corresponding adapter so that the bot account can connect to the core.

For the specific configuration items of each platform's adapter, refer to the [Configuration Guide](/en/guide/configuration.html).

## Step 4: Verify Startup

After completing [Step 2](#step-2-install-and-configure-queqiao) and [Step 3](#step-3-connect-chat-platforms), you can authorize and verify.

### Token Authorization

Log in to the WebUI dashboard and click **Token Authorization** in the "Quick Start" guide card to complete superuser authorization (you can also send the authentication token printed in the console in a group chat on any platform).

::: note
The complete explanation of token authorization (steps, the one-time-use and auto-refresh token mechanism, and how to authorize without WebUI) is available in [WebUI Admin Panel · Token Authorization](/en/guide/webui.html#token-authorization).
:::

### Verify Features

After authorization, the guide card collapses automatically. Now send the following in a chat group:

```
/help
```

If everything is normal, the bot will return the available command list, and you can start using it. Then send `/server` to view the currently online, connected servers.

## FAQ

- **Bot not responding to commands?** Check the `COMMAND_START` prefix, whether `command_groups` contains the current group, and whether `SUPERUSERS` includes your account.
- **Can't connect to the server?** Confirm that the `access_token` on both ends matches, that the WebSocket address and port are reachable, and check the MCDR and bot logs.

For more configuration items, see *[Configuration Guide](/en/guide/configuration.html)*.
