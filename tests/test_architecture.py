"""架构约束测试：锁定分层依赖方向，防止反向依赖回归（见 Refactor.md §3）。"""

import ast
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent / 'Core'
EXTENSION_DIR = CORE_DIR / 'Extension'

# 扩展框架层禁止依赖的上层包（管理域 / 呈现层 / 内置内容）
FORBIDDEN_FOR_EXTENSION = ('Core.Managers', 'Core.Web', 'Core.Builtin')


def _iter_imported_modules(path: Path) -> list[str]:
    """遍历文件内全部导入（含函数内延迟导入），返回被导入的模块名前缀。"""
    tree = ast.parse(path.read_text('Utf-8'))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.append(node.module)
    return modules


def _extension_module_files() -> list[Path]:
    """列出 Core/Extension 下全部模块文件（排除缓存目录）。"""
    return [path for path in EXTENSION_DIR.rglob('*.py') if '__pycache__' not in path.parts]


def test_extension_layer_has_modules():
    """确保测试目标存在，避免路径错误导致空断言。"""
    assert _extension_module_files()


@pytest.mark.parametrize('path', _extension_module_files(), ids=lambda path: path.name)
def test_extension_layer_has_no_upward_imports(path: Path):
    """扩展框架层不得导入管理域 / 呈现层 / 内置内容（含函数内导入）。"""
    offenders = [
        module
        for module in _iter_imported_modules(path)
        if any(module == forbidden or module.startswith(f'{forbidden}.') for forbidden in FORBIDDEN_FOR_EXTENSION)
    ]
    assert not offenders, f'{path.relative_to(CORE_DIR.parent)} imports upward modules: {offenders}'


def test_core_constants_is_dependency_free():
    """Constants 仅依赖标准库，任何模块都可安全导入（不引入 Core 内部依赖）。"""
    offenders = [module for module in _iter_imported_modules(CORE_DIR / 'Constants.py') if module.startswith('Core')]
    assert not offenders, f'Core.Constants must not import Core modules: {offenders}'


def test_i18n_engine_is_dependency_free():
    """I18n 引擎位于 Foundation 层：不得 import Core.Config/Managers/Web/... 等业务模块（不读磁盘、不反向依赖）。"""
    forbidden = (
        'Core.Config',
        'Core.Managers',
        'Core.Extension',
        'Core.Web',
        'Core.Builtin',
        'Core.Platforms',
        'Core.LocaleLoader',
    )
    offenders: list[str] = []
    for path in (CORE_DIR / 'I18n').rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        offenders.extend(
            module
            for module in _iter_imported_modules(path)
            if any(module == item or module.startswith(f'{item}.') for item in forbidden)
        )
    assert not offenders, f'Core.I18n must not import Core business modules: {offenders}'


def test_manifest_does_not_import_base():
    """Manifest 为清单层，不得反向导入 Base（避免 Extension↔Manifest 循环）。"""
    offenders = [
        module
        for module in _iter_imported_modules(EXTENSION_DIR / 'Manifest.py')
        if module == 'Core.Extension.Base' or module.endswith('.Base')
    ]
    assert not offenders, f'Core.Extension.Manifest must not import Base: {offenders}'
