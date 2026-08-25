---
title: "Developing Extensions"
date: 2026-08-21
description: "UniBot extension development guide: write, configure and distribute extensions from scratch — project structure, manifest, command and service registration, rendering templates and marketplace publishing."
---

# Developing Extensions

This document is for extension developers. It explains from scratch how to write, configure, and distribute a UniBot extension. Before you begin, it is recommended to read [Extension System](/en/unibot/extension-system.html) to understand the overall design.

## Extension Development Overview

An extension is a functional unit of UniBot that exposes capabilities to the framework through declarative registration. The basic workflow for developing an extension:

1. Create the extension under `Extensions/` (single-file or directory form).
2. Create an extension instance, declare metadata, and register capability classes.
3. Write the business logic.
4. (Optional) Write the manifest `Extension.toml` to declare dependencies and types.
5. Verify through unit tests and startup logs.

At load time, the framework discovers, validates, and assembles extensions uniformly. Extension code does not need to touch internal details such as the registry or matcher construction.

## Extension Instance

Each code extension must create **exactly one** `Extension` instance during module import, usually named `extension`:

```python
from Scripts.Extensions import Extension

extension = Extension(
    id='WeatherExt',
    name='天气扩展',
    version='1.0.0',
    types=('api', 'command'),
)
```

Metadata can be declared through constructor arguments, or as class attributes on an `Extension` subclass:

```python
from Scripts.Extensions import Extension


class WeatherExtension(Extension):
    id = 'WeatherExt'
    name = '天气扩展'
    version = '1.0.0'
    types = ('api', 'command')


extension = WeatherExtension()
```

Both forms produce exactly the same runtime contract. It is recommended to create the instance at the top of the file and register all capability classes with the `@extension.register_xxx` decorators afterwards.

### Two-Phase Binding

`Extension()` uses two-phase binding:

- **Import phase (unbound)**: the instance only allows reading `config_model` and using the three registration decorators; accessing `metadata`, `config`, `data`, `api`, or `logger` raises `ExtensionNotBoundError`.
- **Bound phase (bound)**: after the Loader validates the entry point and manifest, it injects these capabilities at once through the internal `_bind()`, then runs `on_load()`.

==Extension code must not call `_bind()` directly==; repeated binding must fail. Lifecycle methods only run after binding is complete, so instance capabilities can be safely accessed.

### Capability Registration

`register_command()`, `register_service()` and `register_renderer()` are decorators bound to a specific extension instance: after validating the base class of the passed class, they append the class declaration to that instance and return it unchanged. Capability ownership is determined entirely by the instance used at decoration time — it is never collected via module scanning or method-name guessing.

> `commands` / `services` / `renderers` are the instance's private capability declaration collections, initialized as separate fields by `__init__`; if defined as class attributes, multiple instances would share the same list, causing capabilities to pollute each other.

## Extension Forms and Directory Conventions

### Single-File Extension

Suitable for simple commands; a single file is enough:

```python title="Extensions/Hello.py"
from Scripts.Extensions import Command, Extension

extension = Extension(id='Hello', name='你好', version='1.0.0', types=('command',))


@extension.register_command
class HelloCommand(Command):
    name = 'hello'
    description = '向你问好。'

    async def handler(self) -> str:
        return '你好，世界！'
```

The `extension.id` of a single-file extension must match the file name. Single-file extensions also have the injected `config`, `data`, logger and lifecycle methods; they cannot bypass these boundaries by directly importing internal modules.

### Directory Extension

Suitable for complete extensions with multiple modules, configuration, and dependencies:

```python title="Extensions/WeatherExt/__init__.py"
from Scripts.Extensions import Extension

extension = Extension()

from . import Commands, Services  # noqa: E402,F401
```

The directory name of a directory extension must match `extension.id` exactly (including case). The entry point is fixed at `__init__.py`; if a capability module uses decorators, it should be imported after the `extension` is created, and obtain the instance via `from . import extension`:

> This import order is part of the entry contract: create `extension` first, then import the capability modules that use it.

### Code-Free Extension

`template` and `resources` extensions do not need `__init__.py`; the Loader directly validates the package directory and the declared root directories:

```file-tree
Extensions/Default/
├── Extension.toml
├── Templates/          # Template root directory declared by [template].entry
└── Resources/          # Resources root directory declared by [resources].root
```

Code-free extensions import no Python modules, run no lifecycle hooks, and create no `Extension` instance.

## Writing the `Extension.toml` Manifest

The metadata, compatibility, and dependencies of a directory extension are all declared in the manifest. The manifest is strictly validated by the framework; unknown fields, invalid types, or invalid version constraints will directly block loading.

```toml
[manifest]
schema_version = 1               # Manifest format version

[extension]
id = "WeatherExt"                # Required, PascalCase, matches the directory name
name = "天气扩展"                 # Required
version = "1.0.0"               # Required, semantic version
author = "yourname"             # Optional
description = "扩展描述"          # Optional
types = ["api", "command"]      # api | command | renderer | template | resources

[compatibility]
unibot = ">=0.0.5"              # Compatible bot version constraint, '*' means any

[dependencies]
extensions = ["OtherExt"]       # Dependent extension ids, determines load order
python = []                      # Third-party Python dependencies to install

[renderer]                      # Only needed for renderer extensions
name = "myengine"               # Renderer name, must match BaseRenderer.name

[template]                      # Only needed for template extensions
entry = "Templates"             # Template root directory (relative to the extension package root)
resources = []                  # Optional resource extension ids, forming the resource lookup scope in declaration order

[resources]                     # Only needed for resource extensions
root = "Resources"              # Resources root directory (relative to the extension package root)
```

### Section Reference

::: table title="Manifest Section Reference" copy="all"
| Section | Field | Description |
|----|------|------|
| `[manifest]` | `schema_version` | Manifest format version, currently `1` |
| `[extension]` | `id` | The extension's unique identifier, PascalCase, matches the directory name |
| `[extension]` | `name` / `version` / `author` / `description` | Display information |
| `[extension]` | `types` | Extension type list: `api` / `command` / `renderer` / `template` / `resources` |
| `[compatibility]` | `unibot` | Version constraint, format follows [PEP 440](https://peps.python.org/pep-0440/) |
| `[dependencies]` | `extensions` | Dependent extension ids, used for topological sorting and missing-dependency detection |
| `[dependencies]` | `python` | Third-party Python dependencies to install |
| `[renderer]` | `name` | Renderer name, must match the registered `BaseRenderer.name` |
| `[template]` | `entry` / `resources` | Template root directory and resource dependencies |
| `[resources]` | `root` | Resources root directory |
:::

> Note: the dedicated `renderer`, `template`, and `resources` sections cannot be mixed with other types. `template` and `resources` can be combined in the same extension package, but neither can be mixed with code capabilities.

### Template Config Schema

Code-free templates declare limited flat config fields through `[template.config_schema.<name>]` to customize the template appearance. The first version supports six types, and every field must provide a type and a default value:

```toml
[template.config_schema.primary_color]
type = "color"
default = "#2f80ed"
title = "主色"

[template.config_schema.compact]
type = "boolean"
default = false
title = "紧凑布局"

[template.config_schema.font]
type = "select"
default = "default"
options = ["default", "serif", "mono"]
title = "字体"
```

Constraint rules:

- Field names must be valid Python identifiers and must not start with an underscore.
- `select` must provide a non-empty `options`, and the default value must be included in it.
- Six types are supported: `string`, `integer`, `number`, `boolean`, `color`, `select`.
- Unknown types, unknown constraints, duplicate fields, type mismatches, or invalid default values will directly block template registration.
- Template config supports only basic fields — no expressions, custom validators, or arbitrary types — ensuring code-free packages cannot gain code execution capability.

### Automatic Python Dependency Sync

The `[dependencies].python` declared by extensions is aggregated and deduplicated automatically at load time and written uniformly into the `extensions` group of `[project.optional-dependencies]` in `pyproject.toml`. The Watchdog automatically syncs and installs them at startup and whenever dependency changes are detected; after uninstalling an extension, dependencies are re-aggregated and leftover dependencies are removed only when no other extension uses them.

> Note: the `extensions` group is exclusively maintained by the framework; please do not manually edit that group in `pyproject.toml`.

## Config and Data Directories

Each extension has its own scope-restricted config and data directories; path escape, access to other extensions' directories, or overwriting framework-reserved files are all rejected:

::: table title="Config and Data Directories" copy="all"
| Data | Location | Maintained By | Content |
|------|------|--------|------|
| Extension enable/disable | `Config/Extensions.toml` | User / WebUI | The `enabled` flag for each extension |
| Extension config | `Config/Extensions/<id>.toml` | User / WebUI | Validated business config |
| Management state | `Data/Extension/States.toml` | Framework | Source, version, SHA-256, install time, dependency ownership |
| Business data | `Data/Exs/<id>/` | Extension data utilities | Caches, databases, generated files |
:::

Code extensions access these stores through the bound `extension.config` and `extension.data`, without worrying about path details:

```python
# Read the current config
value = extension.config.value
default_name = value.default_name

# Update the config (validated and atomically persisted; on failure the original config is unchanged)
extension.config.update({'default_name': '张三'})

# Read/write business data
extension.data.write_json('cache.json', {...})
data = extension.data.read_json('cache.json')
```

- `extension.config.value` is the validated current config model; `update()` validates again and atomically replaces the whole config file.
- `ExtensionDataStore` provides path resolution and JSON / text / bytes read-write; all writes are atomic by default, and all relative paths go through escape and reserved-file checks.
- Fields containing secrets in the config only return masked values.

## Developing Command Extensions

Command extensions define the main command by inheriting `Command` and register it with the instance decorator `@extension.register_command`; subcommands are declared as nested `SubCommand` classes.

### A Complete Example

```python
# Extensions/Greet/__init__.py
from Scripts.Extensions import Command, Extension, SubCommand
from nonebot_plugin_alconna import Match

extension = Extension(config_model=None)


@extension.register_command
class GreetCommand(Command):
    """Greeting main command."""

    name = 'greet'
    description = '向某人问好。'
    aliases = ('hi',)  # optional aliases

    def declare(self) -> None:
        """Declare parameters and subcommands."""
        self.register_option('name', str, default='朋友', description='要问候的名字')

    async def handler(self, name: Match[str]) -> str:
        """Handle the greet main command."""
        target = name.result if name.available else '朋友'
        return f'你好，{target}！'

    class Bye(SubCommand):
        """Subcommand: greet bye."""

        name = 'bye'
        description = '道别'

        async def handler(self) -> str:
            return '再见！'
```

### Field Responsibilities

::: table title="Command Field Responsibilities" copy="all"
| Field / Method | Description |
|------------|------|
| `name` | Command name (required) |
| `description` / `usage` / `aliases` | Display and matching metadata |
| `declare()` | Declare parameters and subcommands |
| `handler` | Main command handler; carries the content to send via `return` |
| `image_handler` | Render handler in image mode (optional) |
:::

### Parameter Declaration

Declare parameters in `declare()` with the following methods:

::: table title="Parameter Declaration Methods" copy="all"
| Method | Description |
|------|------|
| `register_arg(name, type, ...)` | Register a required argument |
| `register_option(name, type, default=..., ...)` | Register an optional parameter (with a default value) |
| `register_subcommand(sub)` | Explicitly register a subcommand |
:::

Common options:

- `required`: whether it is required (optional parameters must carry `default`).
- `default`: default value.
- `description`: parameter description, used to generate help.
- `multi=True`: accept multiple values.

`value_type` can be a Python type, an Alconna pattern, or a public type provided by the framework (such as `AtOrText`).

### Handler Return Values

A handler can return:

::: table title="Handler Return Values" copy="all"
| Return Type | Behavior |
|---------|------|
| String | Sent directly as a message |
| Image bytes | Sends a PNG in image mode (with `image_handler`) |
| List | Multiple message fragments, merged and sent by the framework |
| `None` | Nothing is sent |
:::

```python
async def image_handler(self) -> bytes:
    """Render to PNG bytes in image mode."""
    return await extension.render_image('Greet', (500, 0), **data)
```

### Validation Rules

- Duplicate command names, aliases, or parameter names at the same level produce an error including the command id and field path at build time.
- `handler` must be an async callable; signature errors, missing handlers, or branches declared but not registered fail at startup, not when a message is received.
- Each command uses a stable `command_id` (e.g. `builtin:list`, `extension:WeatherExt:weather`).
- Command definitions are fully validated before building; a failed build registers no partial matchers.

## Developing API Service Extensions

Define reusable service capabilities by inheriting `Service` and register them with `@extension.register_service`. Other extensions obtain the service instance via `extension.api.get(ServiceType)`:

```python
from pydantic import BaseModel, Field
from Scripts.Extensions import Extension, Service


class GreetConfig(BaseModel):
    """Business config, used by the WebUI form."""

    default_name: str = Field(default='朋友', description='默认问候名字')


extension = Extension(config_model=GreetConfig)


@extension.register_service
class GreetService(Service):
    """Greeting service."""

    name = 'greet'

    def greet(self, name: str) -> str:
        default = extension.config.value.default_name
        return f'你好，{name or default}！'
```

Use the service in any bound extension:

```python
service = extension.api.get(GreetService)
if service is not None:
    message = service.greet('张三')
```

Load-order guarantees:

- Service dependencies are declared via `[dependencies].extensions`; the Loader topologically sorts them, and the depended-on extensions start first.
- Circular dependencies report an error and skip the related extensions.

## Using the Built-In API Services

UniBot ships two `api` type extensions with the framework, ready to use out of the box, obtained via `extension.api.get(...)`:

::: table title="Built-In API Services" copy="all"
| Extension | Service Class | Registered Name | Description |
|------|--------|--------|------|
| `Players` | `PlayerService` | `player` | Player binding data management |
| `Servers` | `ServerService` | `server` | Minecraft server interaction |
:::

Lookup supports both **service class** and **registered name** forms; looking up by class additionally validates the actual type:

```python
from Scripts.Extensions.Builtin.Services.Players import PlayerService
from Scripts.Extensions.Builtin.Services.Servers import ServerService

player_service = extension.api.get(PlayerService)  # by class; raises TypeError on type mismatch
server_service = extension.api.get('server')  # by registered name
if player_service is None:
    # Service not registered or its extension is disabled; check for None before use
    ...
```

> The built-in services finish initialization during their own extension's `on_enable()` phase (e.g. `ServerService` binds the Minecraft adapter's bot collection), so they are always available in command handlers; `extension.api.get` can only be called from a bound extension.

### PlayerService — Player Account Service

Extension id `Players`; manages the binding between users and game IDs, persisted to `Data/Players.json` as the single source of truth.

::: table title="PlayerService Methods" copy="all"
| Method | Description |
|------|------|
| `players` (property) | All bindings: `{user_id: [player, ...]}` |
| `append_player(user, player) -> bool` | Append a binding for the user, limited by the `qq_bound_max_number` cap; returns `True` on success, `False` when over the limit |
| `remove_player(user, player='') -> list[str]` | Remove a binding; when `player` is empty, removes all bindings of the user and returns the removed player list |
| `check_player_occupied(player) -> bool` | Check whether a game ID is already bound by any user (case-insensitive) |
:::

### ServerService — Minecraft Server Service

Extension id `Servers`; encapsulates server query, command execution, and message broadcast capabilities.

::: table title="ServerService Methods" copy="all"
| Method | Description |
|------|------|
| `servers` (property) | Connected server collection: `{name: Bot}` |
| `get_server(server_flag) -> Bot \| None` | Get a server bot by name or number (starting from 1) |
| `check_online() -> bool` | Whether any server is online |
| `execute(command) -> dict[str, str \| None]` | Execute a console command on all servers; returns `{name: result}`, `None` on failure |
| `get_status(server) -> dict` | Get a single server's status (online, version, player count, CPU, memory, etc.) |
| `get_player_list(server) -> tuple[list[str], int]` | Get a single server's player list and player cap |
| `broadcast(message, except_server='') -> dict[str, None]` | Broadcast a message to all servers, optionally excluding a specific server |
:::

### Example: Broadcast Extension

A complete directory extension example demonstrating how to combine built-in services in a command:

::: code-tree title="Broadcast Extension" height="400px" entry="Extensions/BroadcastExt/__init__.py"
```toml title="Extensions/BroadcastExt/Extension.toml"
[manifest]
schema_version = 1

[extension]
id = "BroadcastExt"
name = "服务器广播"
version = "1.0.0"
types = ["command"]
```

```python title="Extensions/BroadcastExt/__init__.py"
from Scripts.Extensions import Command, Extension, SubCommand
from Scripts.Extensions.Builtin.Services.Servers import ServerService

extension = Extension()


@extension.register_command
class BroadcastCommand(Command):
    """Broadcast a message to all connected servers."""

    name = 'broadcast'
    description = '向所有已连接服务器广播消息。'
    usage = '/broadcast <消息|子命令>'

    def declare(self) -> None:
        self.register_arg('message', str, description='要广播的消息', multi=True)

    async def handler(self, message) -> str | None:
        server_service = extension.api.get(ServerService)
        if server_service is None:
            return '服务器服务不可用。'
        if not server_service.check_online():
            return '没有已连接的服务器。'
        await server_service.broadcast(' '.join(message.result))
        return '广播完成。'

    class Execute(SubCommand['BroadcastCommand']):
        """Execute a console command on all servers."""

        name = 'execute'
        description = '向所有服务器执行控制台指令'

        def declare(self) -> None:
            self.register_arg('command', str, description='要执行的指令', multi=True)

        async def handler(self, command) -> str | None:
            server_service = extension.api.get(ServerService)
            if server_service is None:
                return '服务器服务不可用。'
            results = await server_service.execute(' '.join(command.result))
            return '\n'.join(f'[{name}] {result or "执行失败"}' for name, result in results.items())
```
:::

Key points:

- A `multi=True` parameter is received in the handler as `Match[list[str]]`; join it with `' '.join(...)` into the full content (consistent with the built-in `/send` and `/command`).
- Built-in services are ordinary `api` extensions and are also subject to enable/disable state; when disabled, `get(...)` returns `None`, so check for `None` before use.

## Developing Renderer Extensions

Renderer extensions provide engine capabilities for image rendering. Inherit `BaseRenderer` and implement `setup` / `render` / `shutdown`:

```python
from Scripts.Extensions import BaseRenderer, Extension

extension = Extension(config_model=None)


@extension.register_renderer
class MyRenderer(BaseRenderer):
    name = 'myengine'

    async def setup(self) -> None:
        """Initialize rendering resources."""

    async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        """Render HTML/CSS to PNG bytes (size is the design size, optional)."""
        return png_bytes

    async def shutdown(self) -> None:
        """Release rendering resources."""
```

Declare the renderer type in the manifest:

```toml
[extension]
types = ["renderer"]

[renderer]
name = "myengine"
```

> Note: renderer extensions must not hold global browser instances that are not managed by the manager; concurrency, timeouts, default fallback, and shutdown cleanup are all handled uniformly by `RendererManager`.

### Resource Reference Format

Different renderers may load local / online resources differently: for example, html2pic can read disk paths directly, while Playwright, which is based on a real browser, needs `file://`-prefixed URLs. The framework marks these resources with a unified resource wrapper type, and the renderer decides the final reference format.

::: table title="Resource Wrapper Types" copy="all"
| Wrapper Type | Meaning | Default Conversion |
|---------|------|---------|
| `OnlineAsset(url)` | Online resource (e.g. CDN images) | Returns `url` as-is |
| `FileAsset(path)` | Local file (e.g. avatar cache, fonts) | Returns the disk path `str(path)` |
:::

Renderers can override `deal_online_asset()` / `deal_file_asset()` to adjust the conversion logic:

```python
from Scripts.Extensions import BaseRenderer, Extension, FileAsset


@extension.register_renderer
class MyRenderer(BaseRenderer):
    name = 'myengine'

    def deal_file_asset(self, asset: FileAsset) -> str:
        """Browsers need a file:// prefix to load local files."""
        return asset.path.as_uri()
```

- `deal_online_asset(asset)`: converts an `OnlineAsset` wrapper into a string usable by this renderer; returns `asset.url` by default.
- `deal_file_asset(asset)`: converts a `FileAsset` wrapper into a string usable by this renderer; returns the disk path of `asset.path` by default.

Before rendering, the framework hands the context and the wrappers returned by resource functions to the currently active renderer for conversion, so templates and callers do not need to know about the differences between specific engines.

## Developing Template and Resource Extensions

Template and resource extensions are code-free packages; they do not need `__init__.py` and only participate in static registration.

### Template Extension

```toml
[extension]
id = "MyTemplate"
name = "我的模板"
types = ["template"]

[template]
entry = "Templates"
resources = ["DefaultResources"]

[template.config_schema.primary_color]
type = "color"
default = "#2f80ed"
title = "主色"
```

Template directory structure:

```file-tree
Extensions/MyTemplate/
├── Extension.toml
└── Templates/
    └── Card.html
```

### Resource Extension

```toml
[extension]
id = "DefaultResources"
name = "默认资源"
types = ["resources"]

[resources]
root = "Resources"
```

```file-tree
Extensions/DefaultResources/
├── Extension.toml
└── Resources/
    ├── Backgrounds/
    └── Fonts/
```

### Template Context and Resource Functions

Templates access resources through the Jinja2 functions registered by the framework, without depending on local paths:

```jinja2
<img src="{{ resource_url('DefaultResources', 'Backgrounds/default.png') }}">
```

::: table title="Template Resource Functions" copy="all"
| Function | Description |
|------|------|
| `resource_path(extension_id, relative_path)` | Returns a local file wrapper `FileAsset`; the renderer decides the reference format |
| `resource_url(extension_id, relative_path)` | Returns a local file wrapper `FileAsset` (semantically meaning "reference as a URL") |
| `resource_text(extension_id, relative_path, encoding='Utf-8')` | Reads a UTF-8 text resource, with a file-size limit |
| `resource_bytes(extension_id, relative_path)` | Reads a binary resource, with a file-size limit |
| `random(extension_id, directory)` | Randomly picks an image from the directory and returns a `url("...")` string (internal path converted per renderer) |
:::

The `FileAsset` wrapper returned by resource functions is automatically converted to a usable reference format by the current rendering engine at render time (html2pic uses disk paths, Playwright uses `file://` URLs); templates do not need to care about differences between specific engines.

On every render, the config snapshot of the current template extension is injected into the template context:

```jinja2
{{ config.primary_color }}
{{ config.compact }}
```

Constraints:

- A template can only read its own config; it cannot read or modify other extensions' config.
- The framework reserves the names `config`, `width`, `height`, `font_uri` and the resource functions; caller fields must not override them.
- Template files can only be loaded from directories declared by the extension; escaping via `..`, absolute paths, or symbolic links is forbidden.

### Rendering Invocation

Extensions initiate rendering with `extension.render_image()`:

```python
async def image_handler(self) -> bytes:
    return await extension.render_image('Card', (600, 800), context=data)
```

If the template needs to display resources such as images / fonts, the extension can mark them with resource wrappers in the context and pass them in; the framework hands them to the current renderer for conversion into usable references before rendering:

```python
from pathlib import Path

from Scripts.Extensions import FileAsset, OnlineAsset

return await extension.render_image(
    'Card',
    (600, 800),
    context={
        'background': FileAsset(Path('Data/Avatars/steve.png')),
        'logo': OnlineAsset('https://example.com/logo.png'),
        'badges': [FileAsset(Path(f'Data/Badges/{name}.png')) for name in names],
    },
)
```

- `FileAsset(path)` marks a local file; `OnlineAsset(url)` marks an online URL; the wrappers apply recursively to dicts / lists in the context.
- Use the corresponding key directly in the template, without worrying about reference differences between engines (html2pic / Playwright).
- The template package is selected by the core's `config.image.template`; the `template` parameter is the template name within the package.
- `config` in the Jinja context always comes from the currently selected template package, unrelated to the calling extension's config.
- Unbound state, image mode disabled, missing template, disabled resource dependency, or unavailable renderer all give clear exceptions or logs.

## Lifecycle Hooks

Extensions can participate in lifecycle management through optional coroutine methods:

::: table title="Lifecycle Hooks" copy="all"
| Method | Timing | Purpose |
|------|------|------|
| `on_load()` | After module import and declarations are complete | Read resources, initialize lightweight state |
| `on_enable()` | At startup | Start external resources, connect services |
| `on_disable()` | At shutdown | Release external resources, disconnect |
:::

```python
class WeatherExtension(Extension):
    async def on_enable(self) -> None:
        # Start external services
        await self.client.connect()

    async def on_disable(self) -> None:
        # Release resources
        await self.client.close()
```

Rules:

- `on_load()` / `on_enable()` run in topological order (depended-on extensions run first); on failure, the extensions enabled in this run are rolled back.
- At shutdown, `on_disable()` runs in reverse topological order of dependencies; a single extension's cleanup failure does not block other extensions from shutting down.
- `on_disable()` only releases resources that were started; ==it does not delete config or business data==.

## Overriding Built-In Commands

UniBot ships 8 command extensions with the framework; all are ordinary `Command` classes, and ==every one of them can be overridden through class inheritance==.

::: table title="Built-In Commands" copy="all"
| Extension | Command Class | Command | command_id | Description |
|------|--------|------|------------|------|
| `Bot` | `BotCommand` | `/bot` | `builtin:bot` | Bot management (superusers / about / check / restart) |
| `Bound` | `BoundCommand` | `/bound` | `builtin:bound` | Player whitelist binding (list / query / remove / append) |
| `Command` | `CommandCommand` | `/command` | `builtin:command` | Send console commands to a specific server |
| `Help` | `HelpCommand` | `/help` | `builtin:help` | Command help |
| `List` | `ListCommand` | `/list` | `builtin:list` | Online player list |
| `Luck` | `LuckCommand` | `/luck [rank]` | `builtin:luck` | Daily fortune / fortune ranking |
| `Send` | `SendCommand` | `/send` | `builtin:send` | Send a message to a server |
| `Server` | `ServerCommand` | `/server` | `builtin:server` | Server list |
:::

Command extensions can override any built-in command through **class inheritance**: inherit the built-in `Command` class and override the fields or methods you want to change, while still reusing the inherited business logic. The built-in command classes are imported from `Scripts.Extensions.Builtin.Commands`:

```python
# Extensions/MyListExt/Commands.py
from Scripts.Extensions import Extension
from Scripts.Extensions.Builtin.Commands.List import ListCommand


extension = Extension()


@extension.register_command
class MyListCommand(ListCommand):
    """Only override the output format; the data-fetching logic stays inherited."""

    def list_handler(self, players):
        # Custom output format
        ...
```

Only override part of the behavior, keeping the rest built-in:

```python
# Extensions/MyBotExt/Commands.py
from Scripts.Extensions import Extension
from Scripts.Extensions.Builtin.Commands.Bot import BotCommand


extension = Extension()


@extension.register_command
class MyBotCommand(BotCommand):
    """Keep all /bot subcommands, only replace the restart behavior."""

    def restart_handler(self) -> str:
        return '自定义重启文案。'
```

Rules:

- Inherited fields (`name`, `description`, `usage`, `aliases`), parameters, and subcommands are fully preserved and can be precisely overridden.
- When overriding `handler` / `image_handler` / any business method, it is recommended to mark it with the `@override` decorator from `typing.override` as a coding convention (not mandatory).
- Nested `SubCommand`s can also be inherited and overridden; the `self.parent` chain points to the overridden command instance.
- The Loader automatically recognizes inheritance: a command class inheriting from a built-in command class is treated as an override, registered with the same `builtin:<name>` `command_id` and replacing the built-in definition; otherwise it is registered as a new command with `extension:<extension-id>:<command-name>`. Registering the same `command_id` twice raises an error, avoiding silent override conflicts.

## Extension Config Model

After declaring `config_model` (a Pydantic model), the framework will:

1. Create `Config/Extensions/<id>.toml` for the extension.
2. Validate the file content with `model_validate`; invalid content raises an exception and keeps the old file.
3. Dynamically generate the WebUI config form from the model's JSON Schema.

```python
class WeatherConfig(BaseModel):
    api_key: str = Field(description='天气服务 API Key')
    city: str = Field(default='Shanghai', min_length=1)


extension = Extension(config_model=WeatherConfig)
```

- Extensions without a declared `config_model` use an empty config model and do not accept undeclared fields.
- The WebUI re-validates on config submission; on failure, field-level errors are returned and the original config is unchanged.
- Config store reads/writes are serialized by an instance lock to avoid concurrent read/write races.

## Local Loading and Marketplace Distribution

### Local Loading

Place the extension file or directory into `Extensions/`, then set the enable flag in `Config/Extensions.toml`:

```toml
[MyExt]
enabled = true
```

Extensions not listed are enabled by default. Changing the enable config takes effect after restart.

### Marketplace Distribution

For the complete flow of distributing extensions through the marketplace (packaging, publishing a Release, submitting a metadata PR, SHA-256 verification, and automatic updates),
see [Publishing to the Marketplace](/en/unibot/marketplace.html).

## Development Environment

Extension developers can treat UniBot as an importable package in their editor to get full autocompletion, jump-to-definition, and type checking.

### Mode A: In-Tree Development (Recommended, Zero Config)

- Develop the extension directly under `UniBot/Extensions/`.
- Add `.vscode/settings.json` in the extension directory:

```json
{
    "python.analysis.extraPaths": ["../.."],
    "python.defaultInterpreterPath": "../../.venv/bin/python"
}
```

- The interpreter reuses UniBot's `.venv`, so third-party library hints are correct.
- While developing, just run UniBot's `Bot.py` to debug with the extension loaded.

### Mode B: Standalone Repository Development (Optional)

- In your extension's own `pyproject.toml`, declare UniBot as a local path dependency (editable install).
- Use `uv sync` to install UniBot editable into the extension's own virtual environment.
- If you need to run the full bot, you should still start `Bot.py` in the UniBot workspace.

### Packaging and Publishing

- The template repository provides a packaging script: compress the extension directory into a zip (the zip root is the extension directory, containing `Extension.toml`).
- Upload the zip to GitHub Release and submit an inclusion request to the extension registry.
- For the full publishing flow, see [Publishing to the Marketplace](/en/unibot/marketplace.html).
