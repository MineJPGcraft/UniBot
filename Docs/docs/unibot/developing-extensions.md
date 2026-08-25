---
title: 开发扩展
date: 2026-08-08
description: UniBot 扩展开发指南：从零编写、配置并分发扩展，涵盖项目结构、清单声明、指令与服务注册、渲染模板开发与扩展市场发布流程。
---

# 开发扩展

本文档面向扩展开发者，从零开始介绍如何编写、配置并分发一个 UniBot 扩展。开始之前，建议先阅读 [扩展系统](/unibot/extension-system.html) 了解整体设计。

## 扩展开发总览

扩展是 UniBot 的功能单元，通过声明式注册向框架暴露能力。开发一个扩展的基本流程：

1. 在 `Extensions/` 下创建扩展（单文件或目录型）。
2. 创建扩展实例并声明元数据，注册能力类。
3. 编写业务逻辑。
4. （可选）编写清单 `Extension.toml` 声明依赖与类型。
5. 通过单元测试与启动日志验证。

框架在加载时统一发现、校验并装配扩展，扩展代码不需要接触注册表、匹配器构建等内部细节。

## 扩展实例

每个代码型扩展在模块导入期间必须创建**且仅创建一个** `Extension` 实例，通常命名为 `extension`：

```python
from Scripts.Extensions import Extension

extension = Extension(
    id='WeatherExt',
    name='天气扩展',
    version='1.0.0',
    types=('api', 'command'),
)
```

元数据可通过构造参数声明，也可在 `Extension` 子类上用类属性声明：

```python
from Scripts.Extensions import Extension


class WeatherExtension(Extension):
    id = 'WeatherExt'
    name = '天气扩展'
    version = '1.0.0'
    types = ('api', 'command')


extension = WeatherExtension()
```

两种写法产生完全相同的运行时契约。建议在文件开头创建实例，后续能力类都通过 `@extension.register_xxx` 装饰器登记。

### 两阶段绑定

`Extension()` 采用两阶段绑定：

- **导入阶段（unbound）**：实例只允许读取 `config_model` 与使用三个注册装饰器；访问 `metadata`、`config`、`data`、`api`、`logger` 会抛出 `ExtensionNotBoundError`。
- **绑定阶段（bound）**：Loader 校验入口与清单后，通过内部 `_bind()` 一次性注入这些能力，随后执行 `on_load()`。

==扩展代码不能直接调用 `_bind()`==；重复绑定必须失败。生命周期方法只会在绑定完成后执行，因此可以安全访问实例能力。

### 能力注册

`register_command()`、`register_service()` 与 `register_renderer()` 都是绑定到具体扩展实例的装饰器：校验传入类的基类后，将类声明追加到该实例并原样返回。能力归属完全由装饰时使用的实例决定，不通过模块扫描或方法名猜测收集。

> `commands` / `services` / `renderers` 是实例私有的能力声明集合，由 `__init__` 初始化为独立字段；若定义为类属性，多个实例会共享同一个列表，导致能力互相污染。

## 扩展形态与目录约定

### 单文件扩展

适合简单指令，一个文件即可：

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

单文件扩展的 `extension.id` 必须与文件名一致。单文件扩展同样拥有注入的 `config`、`data`、logger 与生命周期方法；它不能通过直接导入内部模块绕过这些边界。

### 目录型扩展

适合多模块、含配置与依赖的完整扩展：

```python title="Extensions/WeatherExt/__init__.py"
from Scripts.Extensions import Extension

extension = Extension()

from . import Commands, Services  # noqa: E402,F401
```

目录型扩展的目录名与 `extension.id` 必须完全一致（含大小写）。入口固定为 `__init__.py`；能力模块若使用装饰器，应在 `extension` 创建之后导入，并通过 `from . import extension` 获取实例：

> 这条导入顺序是入口契约的一部分：先创建 `extension`，再导入使用它的能力模块。

### 无代码扩展

`template` 与 `resources` 扩展不需要 `__init__.py`，Loader 直接校验包目录与声明的根目录：

```file-tree
Extensions/Default/
├── Extension.toml
├── Templates/          # [template].entry 声明的模板根目录
└── Resources/          # [resources].root 声明的资源根目录
```

无代码扩展不导入 Python 模块、不执行生命周期钩子，也不创建 `Extension` 实例。

> 类型可自由组合：扩展可以同时声明代码能力与无代码类型（如 `types = ["command", "template"]`），
> 此时扩展按普通代码扩展加载（需要 `__init__.py` 入口），其模板/资源部分也会被静态注册。
> 仅当 `types` 只含 `template`/`resources` 时才无需入口文件。

## 编写 `Extension.toml` 清单

目录型扩展的元数据、兼容性与依赖都声明在清单中。清单由框架严格校验，未知字段、非法类型或无效版本约束会直接阻止加载。

```toml
[manifest]
schema_version = 1               # 清单格式版本

[extension]
id = "WeatherExt"                # 必填，PascalCase，与目录名一致
name = "天气扩展"                 # 必填
version = "1.0.0"               # 必填，语义化版本
author = "yourname"             # 可选
description = "扩展描述"          # 可选
types = ["api", "command"]      # api | command | renderer | template | resources

[compatibility]
unibot = ">=0.0.5"              # 兼容的机器人版本约束，'*' 表示任意

[dependencies]
extensions = ["OtherExt"]       # 依赖的其它扩展 id，决定加载顺序
python = []                      # 需安装的第三方 Python 依赖

[renderer]                      # 仅渲染器扩展需要
name = "myengine"               # 渲染器名称，必须与 BaseRenderer.name 一致

[template]                      # 仅模板扩展需要
entry = "Templates"             # 模板根目录（相对扩展包根目录）
resources = []                  # 可选资源扩展 id，按声明顺序组成资源查找范围

[resources]                     # 仅资源扩展需要
root = "Resources"              # 资源根目录（相对扩展包根目录）
```

### 各段说明

::: table title="清单各段说明" copy="all"
| 段 | 字段 | 说明 |
|----|------|------|
| `[manifest]` | `schema_version` | 清单格式版本，当前为 `1` |
| `[extension]` | `id` | 扩展唯一标识，PascalCase，与目录名一致 |
| `[extension]` | `name` / `version` / `author` / `description` | 展示信息 |
| `[extension]` | `types` | 扩展类型列表，`api` / `command` / `renderer` / `template` / `resources` |
| `[compatibility]` | `unibot` | 版本约束，格式遵循 [PEP 440](https://peps.python.org/pep-0440/) |
| `[dependencies]` | `extensions` | 依赖的其它扩展 id，用于拓扑排序与缺失依赖检测 |
| `[dependencies]` | `python` | 需安装的第三方 Python 依赖 |
| `[renderer]` | `name` | 渲染器名称，必须与注册的 `BaseRenderer.name` 一致 |
| `[template]` | `entry` / `resources` | 模板根目录与资源依赖 |
| `[resources]` | `root` | 资源根目录 |
:::

> 注意：`renderer`、`template`、`resources` 专用段只在清单声明了对应类型时生效；五种类型可自由组合，声明 `renderer` 时必须在 `[renderer]` 段提供 `name`。

### 模板配置声明

无代码模板通过 `[template.config_schema.<name>]` 声明受限的扁平配置字段，用于定制模板外观。第一版支持六种类型，每项必须提供类型与默认值：

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

约束规则：

- 字段名必须是合法 Python 标识符且不能以下划线开头。
- `select` 必须提供非空 `options`，默认值必须包含在其中。
- 支持 `string`、`integer`、`number`、`boolean`、`color`、`select` 六种类型。
- 未知类型、未知约束、重复字段、类型不匹配或无效默认值都会直接阻止模板注册。
- 模板配置只支持基础字段，不支持表达式、自定义验证器或任意类型，确保无代码包不会获得代码执行能力。

### Python 依赖自动同步

扩展声明的 `[dependencies].python` 会在加载时自动聚合去重，统一写入 `pyproject.toml` 的 `[project.optional-dependencies].extensions` 组。Watchdog 启动及检测到依赖变化时会自动执行同步安装，无需手动处理；卸载扩展后重新聚合，仅在无其它扩展使用时移除残留依赖。

> 注意：`extensions` 组由框架独占维护，请勿在 `pyproject.toml` 中手动编辑该组。

## 配置与数据目录

每个扩展拥有作用域受限的独立配置与数据目录，路径越界、访问其它扩展目录或覆盖框架保留文件都会被拒绝：

::: table title="配置与数据目录" copy="all"
| 数据 | 位置 | 维护者 | 内容 |
|------|------|--------|------|
| 扩展启停 | `Config/Extensions.toml` | 用户 / WebUI | 每个扩展的 `enabled` 标志 |
| 扩展配置 | `Config/Extensions/<id>.toml` | 用户 / WebUI | 经过校验的业务配置 |
| 管理状态 | `Data/Extension/States.toml` | 框架 | 来源、版本、SHA-256、安装时间、依赖归属 |
| 业务数据 | `Data/Exs/<id>/` | 扩展数据工具 | 缓存、数据库、生成文件 |
:::

代码型扩展通过绑定后的 `extension.config` 与 `extension.data` 访问这些存储，无需关心路径细节：

```python
# 读取当前配置
value = extension.config.value
default_name = value.default_name

# 更新配置（校验并原子持久化，失败不修改原配置）
extension.config.update({'default_name': '张三'})

# 读写业务数据
extension.data.write_json('cache.json', {...})
data = extension.data.read_json('cache.json')
```

- `extension.config.value` 是经过校验的当前配置模型；`update()` 再次校验并整体原子替换配置文件。
- `ExtensionDataStore` 提供路径解析与 JSON / 文本 / 字节读写，所有写操作默认原子提交，所有相对路径都经过越界与保留文件检查。
- 配置包含密钥的字段只返回脱敏值。

## 开发指令扩展

指令扩展通过继承 `Command` 定义主命令，用实例装饰器 `@extension.register_command` 登记；子命令以嵌套 `SubCommand` 类的形式声明。

### 一个完整示例

```python
# Extensions/Greet/__init__.py
from Scripts.Extensions import Command, Extension, SubCommand
from nonebot_plugin_alconna import Match

extension = Extension(config_model=None)


@extension.register_command
class GreetCommand(Command):
    """问候主命令。"""

    name = 'greet'
    description = '向某人问好。'
    aliases = ('hi',)  # 可选别名

    def declare(self) -> None:
        """声明参数与子命令。"""
        self.register_option('name', str, default='朋友', description='要问候的名字')

    async def handler(self, name: Match[str]) -> str:
        """处理 greet 主命令。"""
        target = name.result if name.available else '朋友'
        return f'你好，{target}！'

    class Bye(SubCommand):
        """子命令：greet bye。"""

        name = 'bye'
        description = '道别'

        async def handler(self) -> str:
            return '再见！'
```

### 字段职责

::: table title="Command 字段职责" copy="all"
| 字段 / 方法 | 说明 |
|------------|------|
| `name` | 命令名（必填） |
| `description` / `usage` / `aliases` | 展示与匹配元数据 |
| `declare()` | 声明参数与子命令 |
| `handler` | 主命令处理器，通过 `return` 携带要发送的内容 |
| `image_handler` | 图片模式下的渲染处理器（可选） |
:::

### 参数声明

在 `declare()` 中通过以下方法声明参数：

::: table title="参数声明方法" copy="all"
| 方法 | 说明 |
|------|------|
| `register_arg(name, type, ...)` | 注册必选参数 |
| `register_option(name, type, default=..., ...)` | 注册可选参数（带默认值） |
| `register_subcommand(sub)` | 显式注册子命令 |
:::

常用选项：

- `required`：是否必填（可选参数必须带 `default`）。
- `default`：默认值。
- `description`：参数描述，用于生成帮助。
- `multi=True`：接受多个值。

`value_type` 可使用 Python 类型、Alconna pattern 或框架提供的公共类型（如 `AtOrText`）。

### 处理器返回值

处理器可以返回：

::: table title="处理器返回值" copy="all"
| 返回类型 | 行为 |
|---------|------|
| 字符串 | 直接作为消息发送 |
| 图片字节 | 图片模式下发送 PNG（配合 `image_handler`） |
| 列表 | 多条消息片段，框架合并发送 |
| `None` | 不发送 |
:::

```python
async def image_handler(self) -> bytes:
    """图片模式下渲染为 PNG 字节。"""
    return await extension.render_image('Greet', (500, 0), **data)
```

### 校验规则

- 同一层级的命令名、别名与参数名重复时，在构建阶段给出包含命令 id 与字段路径的错误。
- handler 必须是 async callable；签名错误、缺少 handler 或声明后未注册的分支在启动时失败，不延迟到收到消息时。
- 每个命令使用稳定的 `command_id`（如 `builtin:list`、`extension:WeatherExt:weather`）。
- 命令定义在构建前完成完整校验；构建失败不会注册任何部分匹配器。

## 开发 API 服务扩展

通过继承 `Service` 定义可复用的服务能力，用 `@extension.register_service` 登记。其它扩展通过 `extension.api.get(ServiceType)` 获取服务实例：

```python
from pydantic import BaseModel, Field
from Scripts.Extensions import Extension, Service


class GreetConfig(BaseModel):
    """业务配置，供 WebUI 表单使用。"""

    default_name: str = Field(default='朋友', description='默认问候名字')


extension = Extension(config_model=GreetConfig)


@extension.register_service
class GreetService(Service):
    """问候服务。"""

    name = 'greet'

    def greet(self, name: str) -> str:
        default = extension.config.value.default_name
        return f'你好，{name or default}！'
```

在任一已绑定的扩展中使用服务：

```python
service = extension.api.get(GreetService)
if service is not None:
    message = service.greet('张三')
```

加载顺序保证：

- 服务依赖通过 `[dependencies].extensions` 声明，Loader 拓扑排序，被依赖方先启动。
- 循环依赖报错并跳过相关扩展。

## 使用内置 API 服务

UniBot 随框架内置两个 `api` 类型扩展，开箱即用，通过 `extension.api.get(...)` 获取：

::: table title="内置 API 服务" copy="all"
| 扩展 | 服务类 | 注册名 | 说明 |
|------|--------|--------|------|
| `Players` | `PlayerService` | `player` | 玩家绑定数据管理 |
| `Servers` | `ServerService` | `server` | Minecraft 服务器交互 |
:::

获取方式支持按**服务类**或**注册名**两种写法，按类获取会额外校验实际类型：

```python
from Scripts.Extensions.Builtin.Services.Players import PlayerService
from Scripts.Extensions.Builtin.Services.Servers import ServerService

player_service = extension.api.get(PlayerService)  # 按类获取，类型不匹配抛 TypeError
server_service = extension.api.get('server')  # 按注册名获取
if player_service is None:
    # 服务未注册或所在扩展被禁用，使用前应判空
    ...
```

> 内置服务在各自扩展的 `on_enable()` 阶段完成初始化（如 `ServerService` 绑定 Minecraft 适配器的机器人集合），命令处理器中始终可用；`extension.api.get` 只能在绑定后的扩展中调用。

### PlayerService — 玩家账号服务

扩展 id `Players`，管理用户与游戏 ID 的绑定关系，数据同源落盘 `Data/Players.json`。

::: table title="PlayerService 方法" copy="all"
| 方法 | 说明 |
|------|------|
| `players`（属性） | 全部绑定关系：`{user_id: [player, ...]}` |
| `append_player(user, player) -> bool` | 为用户追加绑定，受 `qq_bound_max_number` 上限约束，成功返回 `True`，超限返回 `False` |
| `remove_player(user, player='') -> list[str]` | 移除绑定；`player` 为空时移除该用户全部绑定，返回被移除的玩家列表 |
| `check_player_occupied(player) -> bool` | 检查游戏 ID 是否已被任意用户绑定（忽略大小写） |
:::

### ServerService — Minecraft 服务器服务

扩展 id `Servers`，封装服务器查询、指令执行与消息广播能力。

::: table title="ServerService 方法" copy="all"
| 方法 | 说明 |
|------|------|
| `servers`（属性） | 已连接服务器集合：`{名称: Bot}` |
| `get_server(server_flag) -> Bot \| None` | 按名称或编号（从 1 开始）获取服务器机器人 |
| `check_online() -> bool` | 是否有服务器在线 |
| `execute(command) -> dict[str, str \| None]` | 向所有服务器执行控制台指令，返回 `{名称: 结果}`，失败为 `None` |
| `get_status(server) -> dict` | 获取单台服务器状态（在线、版本、人数、CPU、内存等） |
| `get_player_list(server) -> tuple[list[str], int]` | 获取单台服务器玩家列表与人数上限 |
| `broadcast(message, except_server='') -> dict[str, None]` | 向所有服务器广播消息，可排除指定服务器 |
:::

### 示例：广播扩展

一个完整的目录型扩展示例，演示如何在命令中组合使用内置服务：

::: code-tree title="广播扩展" height="400px"

```toml title="Extensions/Broadcast/Extension.toml"
[manifest]
schema_version = 1

[extension]
id = "BroadcastExt"
name = "服务器广播"
version = "1.0.0"
types = ["command"]
```

```python title="Extensions/Broadcast/__init__.py" :active
from Scripts.Extensions import Command, Extension, SubCommand
from Scripts.Extensions.Builtin.Services.Servers import ServerService

extension = Extension()


@extension.register_command
class BroadcastCommand(Command):
    """向所有已连接服务器广播消息。"""

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
        """向所有服务器执行控制台指令。"""

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

要点：

- `multi=True` 的参数在 handler 中收到 `Match[list[str]]`，用 `' '.join(...)` 拼接为完整内容（与内置 `/send`、`/command` 一致）。
- 内置服务是普通 `api` 扩展，同样受启停状态控制；被禁用时 `get(...)` 返回 `None`，使用前应判空。

## 开发渲染器扩展

渲染器扩展为图片渲染提供引擎能力，继承 `BaseRenderer` 并实现 `setup` / `render` / `shutdown`：

```python
from Scripts.Extensions import BaseRenderer, Extension

extension = Extension(config_model=None)


@extension.register_renderer
class MyRenderer(BaseRenderer):
    name = 'myengine'

    async def setup(self) -> None:
        """初始化渲染资源。"""

    async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        """将 HTML/CSS 渲染为 PNG 字节（size 为设计尺寸，可选）。"""
        return png_bytes

    async def shutdown(self) -> None:
        """释放渲染资源。"""
```

清单中声明渲染器类型：

```toml
[extension]
types = ["renderer"]

[renderer]
name = "myengine"
```

> 注意：渲染器扩展不得自行持有未由管理器管理的全局浏览器实例；并发、超时、默认回退与退出清理由 `RendererManager` 统一负责。

### 资源引用格式

不同渲染器加载本地 / 在线资源的方式可能不同：例如 html2pic 直接读取磁盘路径即可，而基于真实浏览器的 Playwright 需要带 `file://` 前缀的 URL。框架用统一的资源包装类型标记这些资源，再由渲染器决定最终引用格式。

::: table title="资源包装类型" copy="all"
| 包装类型 | 含义 | 默认转换 |
|---------|------|---------|
| `OnlineAsset(url)` | 在线资源（如 CDN 图片） | 原样返回 `url` |
| `FileAsset(path)` | 本地文件（如头像缓存、字体） | 返回磁盘路径 `str(path)` |
:::

渲染器可覆写 `deal_online_asset()` / `deal_file_asset()` 调整转换逻辑：

```python
from Scripts.Extensions import BaseRenderer, Extension, FileAsset


@extension.register_renderer
class MyRenderer(BaseRenderer):
    name = 'myengine'

    def deal_file_asset(self, asset: FileAsset) -> str:
        """浏览器需带 file:// 前缀才能加载本地文件。"""
        return asset.path.as_uri()
```

- `deal_online_asset(asset)`：把 `OnlineAsset` 包装转换为本渲染器可用的字符串，默认返回 `asset.url`。
- `deal_file_asset(asset)`：把 `FileAsset` 包装转换为本渲染器可用的字符串，默认返回 `asset.path` 的磁盘路径。

框架会在渲染前把上下文与资源函数返回的包装统一交给当前激活的渲染器转换，模板与调用方无需感知具体引擎的差异。

## 开发模板与资源扩展

纯模板与资源扩展是无代码包，不需要 `__init__.py`，只参与静态注册；与代码能力混用时按混合扩展规则加载（需要入口）。

### 模板扩展

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

模板目录结构：

```file-tree
Extensions/MyTemplate/
├── Extension.toml
└── Templates/
    └── Card.html
```

### 资源扩展

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

### 模板上下文与资源函数

模板通过框架注册的 Jinja2 函数访问资源，不直接依赖本地路径：

```jinja2
<img src="{{ resource_url('DefaultResources', 'Backgrounds/default.png') }}">
```

::: table title="模板资源函数" copy="all"
| 函数 | 说明 |
|------|------|
| `resource_path(extension_id, relative_path)` | 返回本地文件包装 `FileAsset`，由渲染器决定引用格式 |
| `resource_url(extension_id, relative_path)` | 返回本地文件包装 `FileAsset`（语义上表示「以 URL 形式引用」） |
| `resource_text(extension_id, relative_path, encoding='Utf-8')` | 读取 UTF-8 文本资源，限制文件大小 |
| `resource_bytes(extension_id, relative_path)` | 读取二进制资源，限制文件大小 |
| `random(extension_id, directory)` | 从目录随机选一张图片，返回 `url("...")` 字符串（内部路径按渲染器转换） |
:::

资源函数返回的 `FileAsset` 包装会在渲染时由当前渲染引擎自动转换为可用的引用格式（html2pic 用磁盘路径、Playwright 用 `file://` URL），模板无需关心具体引擎差异。

每次渲染时，当前模板扩展的配置快照会注入模板上下文：

```jinja2
{{ config.primary_color }}
{{ config.compact }}
```

约束：

- 模板只能读取自身配置，不能读取或修改其它扩展的配置。
- 框架保留 `config`、`width`、`height`、`font_uri` 及资源函数等名称，调用方字段不得覆盖。
- 模板文件只能从扩展声明的目录加载，禁止通过 `..`、绝对路径或符号链接越界。

### 渲染调用

扩展通过 `extension.render_image()` 发起渲染：

```python
async def image_handler(self) -> bytes:
    return await extension.render_image('Card', (600, 800), context=data)
```

若模板需要展示图片 / 字体等资源，扩展可在上下文中用资源包装标记后传入，框架会在渲染前交给当前渲染器转换为可用的引用：

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

- `FileAsset(path)` 标记本地文件，`OnlineAsset(url)` 标记在线 URL；包装会递归作用于上下文中的 dict / list。
- 模板内直接使用对应键即可，无需关心当前引擎（html2pic / Playwright）的引用差异。
- 模板包由核心 `config.image.template` 选择，`template` 参数表示包内模板名称。
- Jinja 上下文中的 `config` 始终来自当前选中的模板包，与调用方扩展的配置无关。
- 未绑定、图片模式关闭、模板不存在、资源依赖未启用或渲染器不可用都会给出明确异常或日志。

## 生命周期钩子

扩展可以通过可选的协程方法参与生命周期管理：

::: table title="生命周期钩子" copy="all"
| 方法 | 时机 | 用途 |
|------|------|------|
| `on_load()` | 模块导入、声明完成后 | 读取资源、初始化轻量状态 |
| `on_enable()` | 启动时 | 启动外部资源、连接服务 |
| `on_disable()` | 关闭时 | 释放外部资源、断开连接 |
:::

```python
class WeatherExtension(Extension):
    async def on_enable(self) -> None:
        # 启动外部服务
        await self.client.connect()

    async def on_disable(self) -> None:
        # 释放资源
        await self.client.close()
```

规则：

- `on_load()` / `on_enable()` 按拓扑顺序执行（被依赖方先执行）；失败时回滚本次已启用的扩展。
- 关闭时按依赖逆拓扑顺序执行 `on_disable()`；单个扩展清理失败不阻止其它扩展关闭。
- `on_disable()` 只释放已启动的资源，==不删除配置或业务数据==。

## 覆盖内置指令

UniBot 随框架内置 8 个命令扩展，全部都是普通 `Command` 类，==每一个都可以通过类继承覆盖==。

::: table title="内置命令一览" copy="all"
| 扩展 | 命令类 | 命令 | command_id | 说明 |
|------|--------|------|------------|------|
| `Bot` | `BotCommand` | `/bot` | `builtin:bot` | 机器人管理（superusers / about / check / restart） |
| `Bound` | `BoundCommand` | `/bound` | `builtin:bound` | 玩家白名单绑定（list / query / remove / append） |
| `Command` | `CommandCommand` | `/command` | `builtin:command` | 向指定服务器发送控制台命令 |
| `Help` | `HelpCommand` | `/help` | `builtin:help` | 命令帮助 |
| `List` | `ListCommand` | `/list` | `builtin:list` | 在线玩家列表 |
| `Luck` | `LuckCommand` | `/luck [rank]` | `builtin:luck` | 今日人品 / 运势排行 |
| `Send` | `SendCommand` | `/send` | `builtin:send` | 向服务器发送消息 |
| `Server` | `ServerCommand` | `/server` | `builtin:server` | 服务器列表 |
:::

指令扩展可以通过**类继承**覆盖任意内置命令：继承内置 `Command` 类并覆写需要修改的字段或方法，业务逻辑仍可继承复用。内置命令类从 `Scripts.Extensions.Builtin.Commands` 导入：

```python
# Extensions/MyListExt/Commands.py
from Scripts.Extensions import Extension
from Scripts.Extensions.Builtin.Commands.List import ListCommand


extension = Extension()


@extension.register_command
class MyListCommand(ListCommand):
    """只覆盖输出格式，数据获取逻辑继承不变。"""

    def list_handler(self, players):
        # 自定义输出格式
        ...
```

只覆写部分行为、其余保持内置：

```python
# Extensions/MyBotExt/Commands.py
from Scripts.Extensions import Extension
from Scripts.Extensions.Builtin.Commands.Bot import BotCommand


extension = Extension()


@extension.register_command
class MyBotCommand(BotCommand):
    """保留 /bot 全部子命令，只替换重启行为。"""

    def restart_handler(self) -> str:
        return '自定义重启文案。'
```

规则：

- 继承后字段（`name`、`description`、`usage`、`aliases`）与参数、子命令完整保留，可精确覆写。
- 覆写 `handler` / `image_handler` / 任意业务方法时，建议使用 `typing.override` 的 `@override` 装饰器作为编码惯例标记（不强制）。
- 嵌套 `SubCommand` 同样可被继承覆盖，`self.parent` 链指向覆写后的命令实例。
- Loader 自动识别继承关系：命令类继承自某内置命令类即判定为覆盖，以同名 `builtin:<name>` 的 `command_id` 注册并取代内置定义；否则作为新增命令以 `extension:<扩展id>:<命令名>` 注册。同一 `command_id` 重复注册会报错，避免静默覆盖冲突。

## 扩展配置模型

声明 `config_model`（Pydantic 模型）后，框架会：

1. 为扩展创建 `Config/Extensions/<id>.toml`。
2. 用 `model_validate` 校验文件内容，非法内容会抛出异常且保留旧文件。
3. 通过模型 JSON Schema 动态生成 WebUI 配置表单。

```python
class WeatherConfig(BaseModel):
    api_key: str = Field(description='天气服务 API Key')
    city: str = Field(default='Shanghai', min_length=1)


extension = Extension(config_model=WeatherConfig)
```

- 未声明 `config_model` 的扩展使用空配置模型，不接受未声明字段。
- WebUI 提交配置时再次校验；校验失败返回字段级错误，不修改原配置。
- 配置存储读写由实例锁串行化，避免并发读写竞争。

## 本地加载与市场分发

### 本地加载

将扩展文件或目录放入 `Extensions/` 后，在 `Config/Extensions.toml` 中设置启停标志：

```toml
[MyExt]
enabled = true
```

未列出的扩展默认启用。修改启停配置后需重启生效。

### 市场分发

通过市场分发扩展的完整流程（打包、发布 Release、提交元数据 PR、SHA-256 校验与自动更新）
请参见 [上传市场](/unibot/marketplace.html)。

## 开发环境

扩展开发者在编辑器中可以把 UniBot 当作可导入的包，获得完整的补全、跳转与类型检查。

### 使用 AiStudio 零代码开发扩展

如果你不想手写代码，可以直接使用 **AiStudio**（UniBot Extension Studio）——官方提供的 AI 扩展开发平台。只需用自然语言描述你想要的扩展，AiStudio 就会自动完成从规划、编码、测试到发布的全部工作，让没有编程经验的用户也能为 UniBot 开发功能。

<ClientOnly>
  <AiStudioDownload />
</ClientOnly>

<script setup>
import AiStudioDownload from '../.vuepress/components/AiStudioDownload.vue'
</script>

#### 核心功能

- **自然语言开发**：在对话中输入一句话描述需求，例如「做一个天气查询指令，支持指定城市，并把结果渲染成图片」。AiStudio 会先理解需求、规划扩展结构，再编写出完整可运行的代码，无需手写任何代码。
- **全流程自动化**：从规划、编码到测试、校验，整个过程由 AiStudio 自动推进。你可以在可视化工作台中实时查看 AI 的思考过程与每一步进度，随时中止或继续。
- **自动测试与修复**：AiStudio 会把自己生成的扩展部署到测试环境并运行测试来验证功能是否正常；如果发现问题，它会根据失败信息自动修复并重新检查，直到通过为止。
- **发布前全面检查**：发布前，平台会对扩展做一次完整的机械检查，确保格式规范、依赖完整、能被机器人安全加载。只有通过检查的扩展才能发布，避免带病扩展影响正在运行的机器人。
- **一键发布**：检查通过后，只需点击「发布」，扩展就会被安装到 UniBot 的扩展目录，重启机器人后即可在聊天中使用。
- **支持多种扩展类型**：除了常见的指令、服务类扩展，AiStudio 同样支持图片渲染模板、资源包等无代码扩展。
- **安全与隐私**：AiStudio 在本地运行，所有数据保存在你自己的电脑上；AI 的操作被限制在独立的草稿工作区，涉及敏感操作会先征询你的确认，不会影响正在运行的机器人。

#### 界面速览

::: table title="界面速览" copy="all"
| 场景 | 截图 |
|------|------|
| **草稿列表**：管理你的扩展草稿，继续开发或查看已发布项目 | ![草稿列表](/images/studio/dashboard.png) |
| **新建扩展**：选择扩展类型、代码类型与目标 MC 服务器后创建 | ![新建扩展](/images/studio/server-referrance.png) |
| **AI 规划**：动工前 AI 向你提问，确认需求方向 | ![AI 规划](/images/studio/ai-plan.png) |
| **编码与自测**：AI 自动部署、运行测试并汇总结果 | ![编码与自测](/images/studio/ai-test.png) |
| **模板开发**：可视化工作台实时展示 AI 的进度 | ![模板开发](/images/studio/template-develop.png) |
| **模板预览**：发布前可放大预览模板渲染效果 | ![模板预览](/images/studio/template-preview.png) |
:::

#### 使用步骤

1. **获取 AiStudio**：在上方表格中下载对应你系统的安装包（表格下方会自动识别你的系统与架构）。也可以直接在 UniBot WebUI 的扩展页面点击右上角「创意工坊」按钮，由 UniBot 自动下载并启动。
2. **打开工作台**：启动后，用浏览器打开 AiStudio 提供的访问地址，即可进入工作台。
3. **描述需求**：用自然语言描述你想要的扩展，尽量说清楚功能与使用方式。
4. **等待完成**：AiStudio 依次完成规划、编码、测试与校验，全程可在界面中查看进度。
5. **发布使用**：校验通过后点击「发布」，重启机器人后即可在聊天中使用新扩展。

> [!TIP]
> AiStudio 面向不会写代码的用户设计，也适合想快速出原型再手工微调的开发者。生成的结果同样遵循本文档介绍的扩展规范，后续可以继续用本文档介绍的方式手动维护。

### 模式 A：树内开发（推荐，零配置）

- 把扩展直接放入 `UniBot/Extensions/` 下开发。
- 在扩展目录添加 `.vscode/settings.json`：

```json
{
    "python.analysis.extraPaths": ["../.."],
    "python.defaultInterpreterPath": "../../.venv/bin/python"
}
```

- 解释器复用 UniBot 的 `.venv`，第三方库提示正确。
- 开发时直接运行 UniBot 的 `Bot.py` 即可带上扩展调试。

### 模式 B：独立仓库开发（可选）

- 扩展自己的 `pyproject.toml` 把 UniBot 声明为本地路径依赖（editable 安装）。
- 通过 `uv sync` 将 UniBot 以可编辑方式装入扩展自己的虚拟环境。
- 若需要运行完整机器人，仍应在 UniBot 工作区启动 `Bot.py`。

### 打包发布

- 模板仓库提供打包脚本：把扩展目录压缩为 zip（zip 根即扩展目录，内含 `Extension.toml`）。
- 将 zip 上传到 GitHub Release，并向扩展注册表提交收录申请。
- 完整发布流程见 [上传市场](/unibot/marketplace.html)。
