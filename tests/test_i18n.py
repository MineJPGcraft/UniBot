"""统一 I18n 引擎、System/Messages 双源保护、按键来源选语言与延迟求值测试。"""

import contextvars
from pathlib import Path

from Core.I18n import (
    DeferredText,
    get_messages_locale,
    get_system_locale,
    i18n,
    i18n_deferred,
    normalize_language,
    register_all,
    register_extension_locales,
    set_messages_locale,
    set_system_locale,
    text,
    text_value,
    unregister_extension_locales,
)


def test_core_text_renders_placeholder() -> None:
    set_messages_locale('zh')
    assert text('core.events.player_join', player='Steve') == '玩家 Steve 加入了游戏。'


def test_missing_language_falls_back_to_default() -> None:
    # 未知语言回退默认语言（zh），仍能取到译文
    assert i18n.render('core.events.player_join', locale='fr', player='Alex') == '玩家 Alex 加入了游戏。'


def test_missing_key_returns_key_with_namespace() -> None:
    # 键缺失返回原文并告警，不抛异常
    assert i18n.render('core.events.not_exist') == 'core.events.not_exist'


def test_system_and_messages_locales_are_independent() -> None:
    # 两个上下文互不干扰：切界面语言不改消息语言，反之亦然
    set_messages_locale('zh')
    set_system_locale('zh')
    try:
        assert text('core.events.player_join', player='Steve') == '玩家 Steve 加入了游戏。'
        assert text('api.auth.token_expired') == 'Token 已过期'
        set_system_locale('en')
        # 界面文案切到英文，机器人消息仍是中文
        assert text('api.auth.token_expired') == 'Token has expired'
        assert text('core.events.player_join', player='Steve') == '玩家 Steve 加入了游戏。'
        set_messages_locale('en')
        set_system_locale('zh')
        # 消息切到英文，界面文案切回中文
        assert text('core.events.player_join', player='Steve') == 'Player Steve joined the game.'
        assert text('api.auth.token_expired') == 'Token 已过期'
    finally:
        set_messages_locale('zh')
        set_system_locale('zh')


def test_api_namespace_follows_system_locale() -> None:
    # 界面文案（api.*，System 文件键）跟随系统语言，与消息语言无关
    set_messages_locale('zh')
    set_system_locale('en')
    try:
        assert i18n.render('api.auth.token_expired', locale=get_system_locale()) == 'Token has expired'
        # 显式传 locale 仍可强制指定语言
        assert i18n.render('api.auth.token_expired', locale='zh') == 'Token 已过期'
    finally:
        set_system_locale('zh')


def test_locale_is_routed_by_source_layer() -> None:
    # 语言按「键来自 System 文件还是 Messages 文件」路由，而非命名空间前缀
    set_messages_locale('en')
    set_system_locale('zh')
    try:
        # System 文件键（扩展名 / 系统指令 / api.*）跟随系统语言
        assert text('builtin.list.name') == '在线玩家'
        assert text('core.commands.bot.description') == '管理机器人。'
        assert text('api.auth.token_expired') == 'Token 已过期'
        # Messages 文件键跟随消息语言
        assert text('core.events.player_join', player='Steve') == 'Player Steve joined the game.'
    finally:
        set_messages_locale('zh')
        set_system_locale('zh')


def test_system_keys_fall_back_to_messages_when_system_unset() -> None:
    # 未显式设置系统语言时（QQ 等机器人场景），System 键回退消息语言，行为与旧版一致
    def _render() -> tuple[str, str]:
        set_messages_locale('en')
        return get_system_locale(), str(i18n_deferred('builtin.list.name'))

    system_locale, name = contextvars.Context().run(_render)
    assert system_locale == 'en'
    assert name == 'Online Players'


def test_normalize_language_parses_accept_header() -> None:
    assert normalize_language('en-US,en;q=0.9') == 'en'
    assert normalize_language('zh-CN,zh;q=0.9') == 'zh'
    assert normalize_language(None) == 'zh'


def test_text_value_returns_list_leaf() -> None:
    # 列表叶子（宜/忌词库）经 text_value 返回为 list，不做占位符格式化
    set_messages_locale('zh')
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
    # 受保护性由「键是否由 System 文件提供」判定
    assert i18n.is_protected('builtin.list.name')
    assert i18n.is_protected('core.commands.bot.description')
    assert i18n.is_protected('api.auth.token_expired')
    assert not i18n.is_protected('core.events.player_join')


def test_deferred_text_resolves_on_str() -> None:
    reference = i18n_deferred('builtin.list.name')
    assert isinstance(reference, DeferredText)
    set_system_locale('zh')
    try:
        assert str(reference) == '在线玩家'
    finally:
        set_system_locale('zh')


def test_deferred_messages_text_follows_messages_locale() -> None:
    # Messages 来源的键跟随消息语言，不受系统语言影响
    reference = i18n_deferred('core.commands.help.description')
    set_system_locale('en')
    set_messages_locale('zh')
    assert str(reference) == '查看所有可用命令的帮助信息。'
    set_messages_locale('en')
    assert str(reference) == 'Show help for all available commands.'
    set_system_locale('zh')
    set_messages_locale('zh')


def test_deferred_system_name_follows_system_locale() -> None:
    # System 来源的键（如扩展/插件显示名）跟随系统语言
    reference = i18n_deferred('builtin.list.name')
    set_messages_locale('zh')
    set_system_locale('zh')
    assert str(reference) == '在线玩家'
    set_system_locale('en')
    assert str(reference) == 'Online Players'
    set_system_locale('zh')


def test_deferred_api_text_follows_system_locale() -> None:
    # api.* 由 System 文件提供，延迟求值应按系统语言解析，且不受消息语言影响
    reference = i18n_deferred('api.auth.token_expired')
    set_messages_locale('en')
    set_system_locale('zh')
    assert str(reference) == 'Token 已过期'
    set_system_locale('en')
    assert str(reference) == 'Token has expired'
    set_system_locale('zh')
    set_messages_locale('zh')


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
    set_messages_locale('en')
    set_system_locale('en')
    try:
        assert get_messages_locale() == 'en'
        assert get_system_locale() == 'en'
    finally:
        set_messages_locale('zh')
        set_system_locale('zh')


def test_is_protected_is_source_based() -> None:
    # 受保护性由「键是否由 System 文件提供」判定：api.* / builtin.* / core.commands.bot.* 受保护
    assert i18n.is_protected('api.auth.token_expired')
    assert i18n.is_protected('builtin.list.name')
    assert i18n.is_protected('core.commands.bot.description')
    # Messages 文件提供的键可覆盖
    assert not i18n.is_protected('core.events.player_join')
    assert not i18n.is_protected('core.commands.list.description')


def test_find_placeholders_dedup_and_order() -> None:
    names = i18n.find_placeholders('玩家 {player} 加入 [{server}]，{player} 加油')
    assert names == ['player', 'server']


def test_catalog_keys_filter_by_prefix() -> None:
    keys = i18n.catalog_keys('zh', 'core.events.')
    assert 'core.events.player_join' in keys
    assert all(key.startswith('core.events.') for key in keys)


def test_base_value_ignores_user_override() -> None:
    i18n.load_override('zh', {'core': {'events': {'player_join': '覆盖：{player}'}}})
    try:
        assert i18n.raw_value('zh', 'core.events.player_join') == '覆盖：{player}'
        assert i18n.base_value('zh', 'core.events.player_join') == '玩家 {player} 加入了游戏。'
    finally:
        register_all()
