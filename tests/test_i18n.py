"""统一 I18n 引擎、System/Messages 双源保护、命名空间与延迟求值测试。"""

from pathlib import Path

from Core.I18n import DeferredText, get_locale, i18n, i18n_text, normalize_language, set_locale, text, text_value
from Core.LocaleLoader import register_all, register_extension_locales, unregister_extension_locales


def test_core_text_renders_placeholder() -> None:
    set_locale('zh')
    assert text('core.events.player_join', player='Steve') == '玩家 Steve 加入了游戏。'


def test_missing_language_falls_back_to_default() -> None:
    # 未知语言回退默认语言（zh），仍能取到译文
    assert i18n.render('core.events.player_join', locale='fr', player='Alex') == '玩家 Alex 加入了游戏。'


def test_missing_key_returns_key_with_namespace() -> None:
    # 键缺失返回原文并告警，不抛异常
    assert i18n.render('core.events.not_exist') == 'core.events.not_exist'


def test_api_namespace_registered_independently() -> None:
    assert i18n.render('api.auth.token_expired', locale='zh') == 'Token 已过期'


def test_normalize_language_parses_accept_header() -> None:
    assert normalize_language('en-US,en;q=0.9') == 'en'
    assert normalize_language('zh-CN,zh;q=0.9') == 'zh'
    assert normalize_language(None) == 'zh'


def test_text_value_returns_list_leaf() -> None:
    # 列表叶子（宜/忌词库）经 text_value 返回为 list，不做占位符格式化
    set_locale('zh')
    good_things = text_value('core.commands.luck.good_things')
    assert isinstance(good_things, list) and all(isinstance(item, str) for item in good_things)


def test_system_layer_cannot_be_overridden() -> None:
    # 系统键（如 builtin.<id>.name）即便写入覆盖层也被忽略
    i18n.load_override('zh', {'builtin': {'list': {'name': '被篡改'}}})
    try:
        assert text('builtin.list.name') == '在线玩家'
    finally:
        register_all()


def test_messages_layer_can_be_overridden() -> None:
    i18n.load_override('zh', {'core': {'events': {'player_join': '覆盖：{player}'}}})
    try:
        assert text('core.events.player_join', player='Steve') == '覆盖：Steve'
    finally:
        register_all()


def test_is_protected_flags_system_keys() -> None:
    assert i18n.is_protected('builtin.list.name')
    assert i18n.is_protected('core.commands.bot.description')
    assert not i18n.is_protected('core.events.player_join')


def test_deferred_text_resolves_on_str() -> None:
    reference = i18n_text('builtin.list.name')
    assert isinstance(reference, DeferredText)
    set_locale('zh')
    try:
        assert str(reference) == '在线玩家'
    finally:
        set_locale('zh')


def test_deferred_text_follows_current_locale() -> None:
    reference = i18n_text('builtin.list.name')
    set_locale('zh')
    assert str(reference) == '在线玩家'
    set_locale('en')
    assert str(reference) == 'Online Players'
    set_locale('zh')


def test_extension_locales_register_and_unregister(tmp_path: Path) -> None:
    (tmp_path / 'zh.toml').write_text('[hello]\ngreeting = "你好 {name}! "\n', encoding='Utf-8')
    (tmp_path / 'en.toml').write_text('[hello]\ngreeting = "Hi {name}!"\n', encoding='Utf-8')
    register_extension_locales('Demo', tmp_path)
    try:
        assert i18n.render('ext.Demo.hello.greeting', locale='zh', name='Steve') == '你好 Steve! '
        assert i18n.render('ext.Demo.hello.greeting', locale='en', name='Steve') == 'Hi Steve!'
    finally:
        unregister_extension_locales('Demo')
    assert not i18n.has('ext.Demo.hello.greeting')


def test_locale_context_roundtrip() -> None:
    set_locale('en')
    try:
        assert get_locale() == 'en'
    finally:
        set_locale('zh')
