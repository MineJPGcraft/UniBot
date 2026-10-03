"""扩展框架·运行时（Runtime）子包：Host 协议、注册容器、依赖同步、加载器、管理器与市场。

Loader 只依赖 Host 协议与 Registry；Manager 实现 Host 并编排生命周期。
本子包单向依赖上层（`Core/Extension/` 本层）的定义/基类模块。
"""
