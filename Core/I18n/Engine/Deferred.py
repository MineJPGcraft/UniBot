"""延迟求值的 I18n 字符串：在被 `str()` 时才按当前语言解析。

用途：扩展 / 插件的**名称与描述**等「注册期拿不到上下文、展示期才需要语言」的文本。
注册时构造 `DeferredText`（不会解析），真正拼接到消息或序列化为 JSON 时才 `str()`
按键来源解析语言（System 文件键跟随系统语言，Messages／扩展键跟随消息语言），因此同一
实例在不同语言请求下得到各自语言的译文。

    name = i18n_deferred('builtin.list.name')   # 构造期不求值
    str(name)                                   # → 当前语言下的「在线玩家」

只需普通字符串的场景（渲染、拼接）请直接用 `Core.I18n.text()`，它立即返回 `str`。
"""

from __future__ import annotations

from typing import Any

from .Manager import i18n


class DeferredText:
    """延迟求值的译文引用，接口上尽量等价 `str`。"""

    __slots__ = ('_key', '_kwargs')

    def __init__(self, key: str, kwargs: dict[str, Any] | None = None) -> None:
        self._key = key
        self._kwargs = kwargs or {}

    @property
    def key(self) -> str:
        """返回底层 I18n 点路径键。"""
        return self._key

    def resolve(self, locale: str | None = None) -> str:
        """在指定（或按键来源自动选定的）语言下解析为字符串。"""
        return i18n.render(self._key, locale=locale, **self._kwargs)

    def __str__(self) -> str:
        return self.resolve()

    def __repr__(self) -> str:
        return self.resolve()

    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)

    def format(self, **kwargs: Any) -> str:
        """先用本引用译文取字符串，再对该字符串做 `.format`。"""
        return str(self).format(**kwargs)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DeferredText):
            return str(self) == str(other)
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def __bool__(self) -> bool:
        return bool(str(self))

    def __add__(self, other: object) -> str:
        return str(self) + str(other)

    def __radd__(self, other: object) -> str:
        return str(other) + str(self)

    def __contains__(self, item: object) -> bool:
        return str(item) in str(self)

    def __len__(self) -> int:
        return len(str(self))

    def __getitem__(self, index: Any) -> str:
        return str(self)[index]


def i18n_deferred(key: str, **kwargs: Any) -> DeferredText:
    """构造延迟求值的译文引用（注册期不求值，`str()` 时按当前语言解析）。"""
    return DeferredText(key, kwargs)
