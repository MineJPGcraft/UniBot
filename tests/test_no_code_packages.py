"""无代码扩展包测试：template/resources 扩展的发现、校验与注册（[types] 含 template/resources）。"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from Scripts.Extensions import ExtensionState, ExtensionType, extension_manager
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
    def test_mixed_code_and_no_code_rejected(self, tmp_path):
        # 代码类型与无代码类型混用在清单解析阶段即被 model_validator 拦截
        with pytest.raises(ManifestError, match='cannot be mixed with code capabilities'):
            parse_manifest(_MIXED_TOML)

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
