"""无代码扩展包测试：template/resources 扩展的发现、校验与注册（[types] 含 template/resources）。

代码能力与无代码类型可混用在同一个扩展中（混合扩展同时走代码加载与静态注册）。
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from Scripts.Extensions import ExtensionState, ExtensionType, command_manager, extension_manager
from Scripts.Extensions.Base import TemplateFieldConfig, parse_manifest
from Scripts.Extensions.Errors import ExtensionError, ManifestError
from Scripts.Extensions.Loader import ExtensionLoader
from Scripts.Extensions.Renderer import build_template_config_model

_TEMPLATE_TOML = """
[manifest]
schema_version = 1

[extension]
id = "TestTemplate"
name = "测试模板"
version = "1.0.0"
author = "test"
description = "测试模板包"
types = ["template"]

[compatibility]
unibot = "*"

[dependencies]
extensions = []
python = []

[template]
entry = "Templates"
resources = ["TestResources"]

[template.config_schema.primary_color]
type = "color"
default = "#8fbc8f"

[template.config_schema.card_radius]
type = "integer"
default = 12
min = 0
max = 48
"""

_RESOURCES_TOML = """
[manifest]
schema_version = 1

[extension]
id = "TestResources"
name = "测试资源"
version = "1.0.0"
author = "test"
description = "测试资源包"
types = ["resources"]

[resources]
root = "Resources"
"""

_MIXED_TOML = """
[manifest]
schema_version = 1

[extension]
id = "Mixed"
name = "混合包"
version = "1.0.0"
author = "test"
description = "代码与无代码混合包"
types = ["template", "api"]

[template]
entry = "Templates"
"""

_COMBINED_TOML = """
[manifest]
schema_version = 1

[extension]
id = "TestCombined"
name = "组合包"
version = "1.0.0"
author = "test"
description = "template+resources 组合无代码包"
types = ["template", "resources"]

[template]
entry = "Templates"

[resources]
root = "Resources"
"""


def _info(tmp_path: Path, toml: str) -> SimpleNamespace:
    """构造一个最小 DiscoveredExtension 替身（仅需要 directory 与 manifest）。"""
    return SimpleNamespace(directory=tmp_path, manifest=parse_manifest(toml))


class TestTemplatePackage:
    def test_commit_template_package_registers_template(self, tmp_path):
        (tmp_path / 'Templates').mkdir()
        info = _info(tmp_path, _TEMPLATE_TOML)
        loader = ExtensionLoader(extension_manager)
        loader._commit_template_package('TestTemplate', info)
        # 展示信息由 _import_and_load 阶段登记（此处模拟）
        loader._register_no_code_display('TestTemplate', info, ExtensionState.enabled, '')
        registration = extension_manager.templates['TestTemplate']
        assert registration.extension_id == 'TestTemplate'
        assert registration.templates_dir == tmp_path / 'Templates'
        assert registration.resource_ids == ('TestResources',)
        # 配置模型编译：默认值可用
        assert registration.config_store.value.primary_color == '#8fbc8f'
        assert registration.config_store.value.card_radius == 12
        # config_schema 暴露在展示信息中
        info = extension_manager.get_extension_info('TestTemplate')
        assert info['types'] == ['template']
        assert info['state'] == 'enabled'
        assert info['config_schema'] == registration.config_model.model_json_schema()

    def test_commit_template_package_missing_entry_raises(self, tmp_path):
        loader = ExtensionLoader(extension_manager)
        with pytest.raises(ManifestError, match='entry directory'):
            loader._commit_template_package('TestTemplate', _info(tmp_path, _TEMPLATE_TOML))

    def test_config_schema_rejects_bad_field_name(self):
        schema = parse_manifest(_TEMPLATE_TOML).template.config_schema
        # 字段名以 _ 开头会被拒绝
        bad = dict(schema)
        bad['_secret'] = TemplateFieldConfig(type='string', default='x')
        with pytest.raises(ExtensionError, match='字段名'):
            build_template_config_model('TestTemplate', bad)

    def test_config_schema_rejects_bad_default(self):
        schema = parse_manifest(_TEMPLATE_TOML).template.config_schema
        bad = dict(schema)
        bad['card_radius'] = TemplateFieldConfig(type='integer', default='12')
        with pytest.raises(ExtensionError, match='default must be'):
            build_template_config_model('TestTemplate', bad)


class TestResourcesPackage:
    def test_commit_resources_package_registers_resources(self, tmp_path):
        (tmp_path / 'Resources').mkdir()
        loader = ExtensionLoader(extension_manager)
        loader._commit_resources_package('TestResources', _info(tmp_path, _RESOURCES_TOML))
        assert extension_manager.resources['TestResources'] == tmp_path / 'Resources'

    def test_commit_resources_package_missing_root_raises(self, tmp_path):
        loader = ExtensionLoader(extension_manager)
        with pytest.raises(ManifestError, match='root directory'):
            loader._commit_resources_package('TestResources', _info(tmp_path, _RESOURCES_TOML))


class TestCommitNoCodePackage:
    def test_mixed_manifest_allowed(self):
        # 代码类型与无代码类型允许混用在同一个清单中
        manifest = parse_manifest(_MIXED_TOML)
        assert set(manifest.extension.types) == {ExtensionType.template, ExtensionType.api}

    def test_mixed_commit_registers_template_part(self, tmp_path):
        # 混合扩展的无代码部分照常静态注册
        (tmp_path / 'Templates').mkdir()
        loader = ExtensionLoader(extension_manager)
        loader._commit_no_code_package('Mixed', _info(tmp_path, _MIXED_TOML))
        assert 'Mixed' in extension_manager.templates
        assert extension_manager.templates['Mixed'].templates_dir == tmp_path / 'Templates'

    def test_combined_template_resources_registers_both(self, tmp_path):
        # template+resources 组合包：一次提交同时注册模板与资源
        (tmp_path / 'Templates').mkdir()
        (tmp_path / 'Resources').mkdir()
        info = _info(tmp_path, _COMBINED_TOML)
        loader = ExtensionLoader(extension_manager)
        loader._commit_no_code_package('TestCombined', info)
        assert 'TestCombined' in extension_manager.templates
        assert extension_manager.templates['TestCombined'].templates_dir == tmp_path / 'Templates'
        assert extension_manager.resources['TestCombined'] == tmp_path / 'Resources'

    def test_no_code_display_entry_does_not_enter_registry(self, tmp_path):
        # 无代码包不创建 Extension 实例，不进 registry
        (tmp_path / 'Templates').mkdir()
        info = _info(tmp_path, _TEMPLATE_TOML)
        loader = ExtensionLoader(extension_manager)
        loader._commit_template_package('TestTemplate', info)
        loader._register_no_code_display('TestTemplate', info, ExtensionState.enabled, '')
        assert 'TestTemplate' not in extension_manager.registry
        assert extension_manager.no_code_info['TestTemplate']['state'] == 'enabled'


class TestExtensionTypes:
    def test_extension_type_enum_values(self):
        assert ExtensionType.api.value == 'api'
        assert ExtensionType.command.value == 'command'
        assert ExtensionType.renderer.value == 'renderer'
        assert ExtensionType.template.value == 'template'
        assert ExtensionType.resources.value == 'resources'
        # render 类型已删除
        assert 'render' not in {t.value for t in ExtensionType}


# ===== 混合扩展（代码 + 无代码）端到端加载 =====

_HYBRID_TOML = """
[manifest]
schema_version = 1

[extension]
id = "Hybrid"
name = "混合扩展"
version = "1.0.0"
types = ["template", "command"]

[template]
entry = "Templates"

[template.config_schema.title]
type = "string"
default = "hi"
"""

_HYBRID_CODE = """\
from Scripts.Extensions import Command, Extension

extension = Extension(id="Hybrid", name="Hybrid", version="1.0.0", types=("template", "command"))


@extension.register_command
class PingCommand(Command):
    name = 'ping'
    description = 'hybrid ping'

    async def handler(self) -> str:
        return 'pong'
"""


class TestHybridExtension:
    @pytest.fixture
    def hybrid_extension_dir(self, tmp_path, monkeypatch):
        """隔离的临时扩展环境（内置目录重定向为空目录）。"""
        extension_dir = tmp_path / 'Extensions'
        extension_dir.mkdir()
        builtin_dir = tmp_path / 'Builtin'
        (builtin_dir / 'Commands').mkdir(parents=True)
        (builtin_dir / 'Services').mkdir()
        ext_dir = extension_dir / 'Hybrid'
        (ext_dir / 'Templates').mkdir(parents=True)
        (ext_dir / 'Extension.toml').write_text(_HYBRID_TOML, encoding='Utf-8')
        (ext_dir / '__init__.py').write_text(_HYBRID_CODE, encoding='Utf-8')
        sys.path.insert(0, str(tmp_path))
        monkeypatch.setattr('Scripts.Extensions.Loader.EXTENSIONS_DIR', extension_dir)
        monkeypatch.setattr('Scripts.Extensions.Loader.BUILTIN_DIR', builtin_dir)
        monkeypatch.setattr('Scripts.Extensions.Loader.CONFIG_ROOT', tmp_path / 'Config')
        monkeypatch.setattr('Scripts.Extensions.Loader.DATA_ROOT', tmp_path / 'Data')
        yield extension_dir
        sys.path.remove(str(tmp_path))
        for name in list(sys.modules):
            if name.startswith('Extensions.'):
                sys.modules.pop(name, None)
        command_manager.cleanup_matchers()

    def test_hybrid_loads_code_and_template_parts(self, hybrid_extension_dir):
        extension_manager.load()

        # 代码部分：进入 registry，命令已注册
        extension = extension_manager.registry['Hybrid']
        assert extension.state is ExtensionState.loaded
        assert set(extension.metadata.types) == {ExtensionType.template, ExtensionType.command}
        assert 'extension:Hybrid:ping' in command_manager._commands
        # 无代码部分：模板包已静态注册（配置 schema 编译自清单）
        registration = extension_manager.templates['Hybrid']
        assert registration.templates_dir == hybrid_extension_dir / 'Hybrid' / 'Templates'
        assert registration.config_store.value.title == 'hi'
        # 混合扩展以 registry 实例为准，不写 no_code_info
        assert 'Hybrid' not in extension_manager.no_code_info
        info = extension_manager.get_extension_info('Hybrid')
        assert info['types'] == ['template', 'command']
        assert info['state'] == 'loaded'

    def test_pure_no_code_package_still_skips_entry_module(self, hybrid_extension_dir):
        # 纯无代码包仍无需 __init__.py 入口
        tpl_dir = hybrid_extension_dir / 'Tpl'
        (tpl_dir / 'Templates').mkdir(parents=True)
        (tpl_dir / 'Extension.toml').write_text(_TEMPLATE_TOML.replace('TestTemplate', 'Tpl'), encoding='Utf-8')

        extension_manager.load()

        assert 'Tpl' not in extension_manager.registry
        assert extension_manager.no_code_info['Tpl']['state'] == 'enabled'
