"""扩展框架·运行时（Runtime）子包：加载器、依赖同步、顶层管理器与两类组件目录。

- `Manager.py`：`ExtensionManager` 顶层组合器——创建注册容器并交给 Loader，编排生命周期与热重载
- `Loader.py`：发现、校验、拓扑排序与导入加载；`Dependencies.py`：依赖同步
- `Registries/`：扩展本体与五类扩展能力（api/command/renderer/template/resources）的纯注册容器
- `Managers/`：各类型管理器的校验、构建与编排（Command / Service / Renderer）

`ExtensionManager` 创建 `ExtensionRegistries` 后按引用交给 Loader 与各管理器；
本子包单向依赖上层（`Core/Extension/` 本层）的定义/基类模块，定义模块不得导入本子包实现。
"""
