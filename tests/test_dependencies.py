"""
扩展依赖收集与同步计划测试。

验证方案：以 uv 命令为唯一写入通道后，本模块只负责「算出增删计划」与
「构造 uv 命令」，因此测试全部针对纯函数，不执行任何真实 uv 命令。

覆盖点：
- 未启用的扩展不参与依赖收集（也不参与保留集合）；
- extensions 组由框架独占，组内无扩展声明的条目会被计划移除；
- 仍被已启用扩展使用的共享依赖不会被移除；
- 计划幂等：pyproject 已与声明一致时增删清单均为空；
- uv 命令参数顺序与 `--inexact` 约定正确。
"""

import textwrap
from pathlib import Path

from Scripts.Extensions import Dependencies


def _write_extension(root: Path, name: str, python_deps: list[str]) -> None:
    """在临时 Extensions/ 下写入一个扩展目录及其 Extension.toml。"""
    ext_dir = root / 'Extensions' / name
    ext_dir.mkdir(parents=True)
    deps = ', '.join(f'"{dep}"' for dep in python_deps)
    (ext_dir / 'Extension.toml').write_text(
        textwrap.dedent(
            f"""
            [extension]
            id = "{name}"

            [dependencies]
            python = [{deps}]
            """
        ),
        encoding='Utf-8',
    )


def _write_enabled_config(root: Path, disabled: list[str]) -> None:
    """写入 Config/Extensions.toml，将指定扩展标记为禁用。"""
    config_dir = root / 'Config'
    config_dir.mkdir(parents=True)
    lines = []
    for name in disabled:
        lines.append(f'[{name}]')
        lines.append('enabled = false')
    (config_dir / 'Extensions.toml').write_text('\n'.join(lines), encoding='Utf-8')


def _write_pyproject(root: Path, extensions: list[str]) -> None:
    """写入带 extensions 可选组的 pyproject.toml。"""
    deps = ', '.join(f'"{dep}"' for dep in extensions)
    (root / 'pyproject.toml').write_text(
        textwrap.dedent(
            f"""
            [project]
            name = "test"

            [project.optional-dependencies]
            extensions = [{deps}]
            """
        ),
        encoding='Utf-8',
    )


def _write_config_toml(root: Path, *, webui_enabled: bool) -> None:
    """写入 Config.toml（用于验证已启用 extras 的读取）。"""
    (root / 'Config.toml').write_text(
        textwrap.dedent(
            f"""
            [webui]
            enabled = {str(webui_enabled).lower()}
            """
        ),
        encoding='Utf-8',
    )


def _setup(tmp_path: Path, monkeypatch) -> None:
    """把 Dependencies 模块的路径常量指向临时目录。"""
    monkeypatch.setattr(Dependencies, 'EXTENSIONS_DIR', tmp_path / 'Extensions')
    monkeypatch.setattr(Dependencies, 'CONFIG_EXTENSIONS_FILE', tmp_path / 'Config' / 'Extensions.toml')
    monkeypatch.setattr(Dependencies, 'CONFIG_TOML_PATH', tmp_path / 'Config.toml')
    monkeypatch.setattr(Dependencies, 'PYPROJECT_PATH', tmp_path / 'pyproject.toml')


# ===== 依赖收集 =====


class TestCollectExtensionDependencies:
    def test_disabled_extension_dependencies_skipped(self, tmp_path, monkeypatch):
        """未启用的扩展不参与依赖收集。"""
        _write_extension(tmp_path, 'EnabledExt', ['dep-a', 'dep-common'])
        _write_extension(tmp_path, 'DisabledExt', ['dep-b', 'dep-common'])
        _write_enabled_config(tmp_path, ['DisabledExt'])
        _setup(tmp_path, monkeypatch)

        collected = Dependencies.collect_extension_dependencies()
        assert sorted(collected) == ['dep-a', 'dep-common']

    def test_missing_enabled_config_defaults_to_enabled(self, tmp_path, monkeypatch):
        """Config/Extensions.toml 缺失时默认全部启用（与 Loader 语义一致）。"""
        _write_extension(tmp_path, 'ExtA', ['dep-a'])
        _write_extension(tmp_path, 'ExtB', ['dep-b'])
        _setup(tmp_path, monkeypatch)

        collected = Dependencies.collect_extension_dependencies()
        assert sorted(collected) == ['dep-a', 'dep-b']


# ===== 包名提取 =====


class TestPackageName:
    def test_plain_name(self):
        """无约束的声明原样返回。"""
        assert Dependencies.package_name('nonebot-plugin-htmlrender') == 'nonebot-plugin-htmlrender'

    def test_strips_extras_and_version(self):
        """去除 extras 与版本约束。"""
        assert Dependencies.package_name('playwright>=1.40.0') == 'playwright'
        assert Dependencies.package_name('httpx[http2]==0.27.0') == 'httpx'

    def test_strips_marker(self):
        """去除 PEP 508 环境标记部分。"""
        assert Dependencies.package_name('tomli; python_version < "3.11"') == 'tomli'


# ===== 同步计划 =====


class TestPlanExtensionDependencyChanges:
    def test_adds_enabled_only(self, tmp_path, monkeypatch):
        """仅追加已启用扩展声明的依赖。"""
        _write_extension(tmp_path, 'EnabledExt', ['dep-a'])
        _write_extension(tmp_path, 'DisabledExt', ['dep-b'])
        _write_enabled_config(tmp_path, ['DisabledExt'])
        _write_pyproject(tmp_path, [])
        _setup(tmp_path, monkeypatch)

        to_add, to_remove = Dependencies.plan_extension_dependency_changes()
        assert to_add == ['dep-a']
        assert to_remove == []

    def test_prunes_undeclared_entries(self, tmp_path, monkeypatch):
        """extensions 组由框架独占：无扩展声明的条目进入移除计划。"""
        _write_extension(tmp_path, 'EnabledExt', ['dep-a'])
        _write_pyproject(tmp_path, ['dep-a', 'dep-uninstalled'])
        _setup(tmp_path, monkeypatch)

        to_add, to_remove = Dependencies.plan_extension_dependency_changes()
        assert to_add == []
        assert to_remove == ['dep-uninstalled']

    def test_keeps_shared_dependency(self, tmp_path, monkeypatch):
        """仍被已启用扩展使用的共享依赖不会被移除。"""
        _write_extension(tmp_path, 'FirstExt', ['dep-shared'])
        _write_extension(tmp_path, 'SecondExt', ['dep-shared'])
        _write_pyproject(tmp_path, ['dep-shared'])
        _setup(tmp_path, monkeypatch)

        to_add, to_remove = Dependencies.plan_extension_dependency_changes()
        assert to_add == []
        assert to_remove == []

    def test_disabled_extension_loses_dependency(self, tmp_path, monkeypatch):
        """扩展被禁用后，其独占依赖进入移除计划。"""
        _write_extension(tmp_path, 'DisabledExt', ['dep-b'])
        _write_enabled_config(tmp_path, ['DisabledExt'])
        _write_pyproject(tmp_path, ['dep-b'])
        _setup(tmp_path, monkeypatch)

        to_add, to_remove = Dependencies.plan_extension_dependency_changes()
        assert to_add == []
        assert to_remove == ['dep-b']

    def test_plan_is_idempotent(self, tmp_path, monkeypatch):
        """pyproject 已与声明一致时，增删清单均为空。"""
        _write_extension(tmp_path, 'EnabledExt', ['dep-a>=1.0'])
        _write_pyproject(tmp_path, ['dep-a>=1.0'])
        _setup(tmp_path, monkeypatch)

        to_add, to_remove = Dependencies.plan_extension_dependency_changes()
        assert to_add == []
        assert to_remove == []


# ===== uv 命令构造 =====


class TestUvCommandBuilders:
    def test_add_command_uses_optional_extra(self):
        """新增走 uv add --optional <extra> --no-sync。"""
        assert Dependencies.build_uv_add_command(['dep-a']) == [
            'uv',
            'add',
            '--optional',
            'extensions',
            '--no-sync',
            'dep-a',
        ]

    def test_remove_command_puts_flag_before_packages(self):
        """uv remove 的 --optional 必须排在包名之前才能被 CLI 接受。"""
        command = Dependencies.build_uv_remove_command(['dep-a'])
        assert command.index('--optional') < command.index('dep-a')

    def test_main_add_and_remove_commands(self):
        """插件依赖走 project.dependencies（不带 --optional）。"""
        assert Dependencies.build_uv_add_main_command(['dep-a']) == ['uv', 'add', '--no-sync', 'dep-a']
        assert Dependencies.build_uv_remove_main_command(['dep-a']) == ['uv', 'remove', '--no-sync', 'dep-a']

    def test_sync_command_includes_inexact_and_extras(self, tmp_path, monkeypatch):
        """uv sync 必须带 --inexact 并包含全部已启用 extras 与 extensions。"""
        _write_config_toml(tmp_path, webui_enabled=True)
        _setup(tmp_path, monkeypatch)

        command = Dependencies.build_uv_sync_command()
        assert command[:3] == ['uv', 'sync', '--inexact']
        assert '--extra' in command
        assert 'webui' in command
        assert 'extensions' in command

    def test_sync_command_skips_disabled_extras(self, tmp_path, monkeypatch):
        """未启用的可选功能不应出现在 uv sync 的 extra 列表中。"""
        _write_config_toml(tmp_path, webui_enabled=False)
        _setup(tmp_path, monkeypatch)

        command = Dependencies.build_uv_sync_command()
        assert 'webui' not in command
        assert 'extensions' in command
