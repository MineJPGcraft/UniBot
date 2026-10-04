"""A0 契约测试：错误模型、状态机、清单校验。"""

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from Core.Extension import (
    Extension,
    ExtensionError,
    ExtensionState,
    ManifestError,
    parse_manifest,
)

# ===== manifest 校验 =====


class TestManifestParsing:
    def test_valid_manifest(self):
        content = """
[manifest]
schema_version = 1

[extension]
id = "WeatherExt"
name = "天气扩展"
version = "1.0.0"
author = "UniBot"
description = "示例扩展"
types = ["api", "command"]

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = ["OtherExt"]
python = []
"""
        manifest = parse_manifest(content)
        assert manifest.extension.id == 'WeatherExt'
        assert manifest.extension.types == ['api', 'command']
        assert manifest.compatibility.unibot == '>=0.0.5'
        assert manifest.dependencies.extensions == ['OtherExt']

    def test_invalid_id_rejected(self):
        content = """
[manifest]
schema_version = 1

[extension]
id = "bad-id!"
name = "x"
version = "1.0.0"
author = "x"
description = "x"
types = ["api"]

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = []
python = []
"""
        with pytest.raises(ManifestError):
            parse_manifest(content)

    def test_invalid_type_rejected(self):
        content = """
[manifest]
schema_version = 1

[extension]
id = "FooExt"
name = "x"
version = "1.0.0"
author = "x"
description = "x"
types = ["not_a_real_type"]

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = []
python = []
"""
        with pytest.raises(ManifestError):
            parse_manifest(content)

    def test_unknown_field_rejected(self):
        content = """
[manifest]
schema_version = 1

[extension]
id = "FooExt"
name = "x"
version = "1.0.0"
author = "x"
description = "x"
types = ["api"]
unexpected_field = "boom"

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = []
python = []
"""
        with pytest.raises(ManifestError):
            parse_manifest(content)

    def test_missing_required_field_rejected(self):
        content = """
[manifest]
schema_version = 1

[extension]
id = "FooExt"
version = "1.0.0"
author = "x"
types = ["api"]

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = []
python = []
"""
        with pytest.raises(ManifestError):
            parse_manifest(content)


# ===== 状态机 =====


class TestStateMachine:
    def test_default_state_is_discovered(self):
        assert Extension().state is ExtensionState.discovered

    def test_valid_transitions(self):
        ext = Extension()
        _bind_fake(ext)
        ext.transition(ExtensionState.validated)
        ext.transition(ExtensionState.loaded)
        assert ext.state is ExtensionState.loaded
        ext.transition(ExtensionState.enabled)
        assert ext.state is ExtensionState.enabled
        ext.transition(ExtensionState.disabled)
        assert ext.state is ExtensionState.disabled

    def test_invalid_transition_raises(self):
        ext = Extension()
        _bind_fake(ext)
        with pytest.raises(ExtensionError):
            # discovered -> enabled 非法（缺 loaded）
            ext.transition(ExtensionState.enabled)

    def test_mark_failed_sets_reason(self):
        ext = Extension()
        _bind_fake(ext)
        ext.mark_failed('加载失败')
        assert ext.state is ExtensionState.failed
        assert ext.failure_reason == '加载失败'


# ===== Extension 基类 =====


class TestExtensionBase:
    def test_default_config_model_rejects_unknown_fields(self):
        ext = Extension()
        assert ext.config_model is not None
        with pytest.raises(ValidationError):
            ext.config_model.model_validate({'unknown': 1})

    def test_id_is_plain_class_attribute(self):
        ext = Extension()
        assert ext.id == ''  # 未声明时基类缺省为空串

        class FakeExt(Extension):
            id = 'Fake'

        assert FakeExt().id == 'Fake'

    def test_id_synced_from_metadata_on_bind(self):
        ext = Extension()
        _bind_fake(ext)
        assert ext.id == 'WeatherExt'

    def test_double_bind_raises(self):
        ext = Extension()
        _bind_fake(ext)
        with pytest.raises(ExtensionError):
            _bind_fake(ext)

    def test_get_config_schema_returns_schema(self):
        class Cfg(BaseModel):
            model_config = ConfigDict(extra='forbid')
            api_key: str = Field(description='key')

        ext = Extension()
        ext.config_model = Cfg
        schema = ext.get_config_schema()
        assert schema['properties']['api_key']['description'] == 'key'


# ===== 工具函数 =====


def _fake_metadata():
    from Core.Extension import ExtensionMetadata

    manifest = parse_manifest("""
[manifest]
schema_version = 1

[extension]
id = "WeatherExt"
name = "天气扩展"
version = "1.0.0"
author = "UniBot"
description = "示例扩展"
types = ["api"]

[compatibility]
unibot = ">=0.0.5"

[dependencies]
extensions = []
python = []
""")
    return ExtensionMetadata(manifest)


def _bind_fake(ext: Extension) -> None:
    """将扩展绑定到一个伪造 metadata，供状态机/属性测试使用。"""
    ext._bind(metadata=_fake_metadata(), config_store=None, data_store=None, api=None, renderer_manager=None)
