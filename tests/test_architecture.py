"""架构约束测试：锁定分层依赖方向，防止反向依赖回归（见 Refactor.md §3）。"""

import ast
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent / 'Core'
EXTENSION_DIR = CORE_DIR / 'Extension'
REPO_ROOT = CORE_DIR.parent

# 扩展框架层禁止依赖的上层包（管理域 / 呈现层 / 内置内容）
FORBIDDEN_FOR_EXTENSION = ('Core.Managers', 'Core.Web', 'Core.Builtin')

# 定义层（扩展作者继承/导入的模块，位于 Core/Extension 根）禁止在运行期依赖的子包
FORBIDDEN_FOR_DEFINITIONS = ('Core.Extension.Runtime', 'Core.Extension.Market')


def _module_name(path: Path) -> str:
    """由文件路径推导模块全名（`Core/Extension/Runtime/Loader.py` → `Core.Extension.Runtime.Loader`）。"""
    parts = list(path.relative_to(REPO_ROOT).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(parts)


def _iter_imported_modules(path: Path, *, include_type_checking: bool = False) -> list[str]:
    """
    遍历文件内全部导入（含函数内延迟导入），返回被导入的模块名。

        相对导入按所在包解析为绝对模块名；`if TYPE_CHECKING:` 块内的导入默认忽略
        （运行期不存在，不构成真实依赖）。
    """
    tree = ast.parse(path.read_text('Utf-8'))
    type_checking_nodes = set() if include_type_checking else _type_checking_nodes(tree)
    package = _module_name(path).split('.')[:-1]
    modules: list[str] = []
    for node in ast.walk(tree):
        if any(node is child for parent in type_checking_nodes for child in ast.walk(parent)):
            continue
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level == 0:
            if node.module:
                modules.append(node.module)
            continue
        # 相对导入：level 1 = 同包，向上每多一级减一层
        base = package[: len(package) - (node.level - 1)] if node.level > 1 else package
        modules.append('.'.join([*base, node.module]) if node.module else '.'.join(base))
    return modules


def _type_checking_nodes(tree: ast.AST) -> list[ast.If]:
    """返回所有 `if TYPE_CHECKING:` 语句节点。"""
    nodes: list[ast.If] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Name):
            continue
        if node.test.id == 'TYPE_CHECKING':
            nodes.append(node)
    return nodes


def _extension_module_files() -> list[Path]:
    """列出 Core/Extension 下全部模块文件（排除缓存目录）。"""
    return [path for path in EXTENSION_DIR.rglob('*.py') if '__pycache__' not in path.parts]


def _definition_module_files() -> list[Path]:
    """列出定义层模块（Core/Extension 根的非 `__init__` 模块，供扩展作者直接导入）。"""
    return [path for path in EXTENSION_DIR.glob('*.py') if path.name != '__init__.py']


def _matches(module: str, prefixes: tuple[str, ...]) -> bool:
    """模块名是否命中任一层级前缀（自身或其后代）。"""
    return any(module == prefix or module.startswith(f'{prefix}.') for prefix in prefixes)


def test_extension_layer_has_modules():
    """确保测试目标存在，避免路径错误导致空断言。"""
    assert _extension_module_files()


@pytest.mark.parametrize('path', _extension_module_files(), ids=lambda path: path.name)
def test_extension_layer_has_no_upward_imports(path: Path):
    """扩展框架层不得导入管理域 / 呈现层 / 内置内容（含函数内导入）。"""
    offenders = [module for module in _iter_imported_modules(path) if _matches(module, FORBIDDEN_FOR_EXTENSION)]
    assert not offenders, f'{path.relative_to(CORE_DIR.parent)} imports upward modules: {offenders}'


@pytest.mark.parametrize('path', _definition_module_files(), ids=lambda path: path.name)
def test_extension_definitions_do_not_import_subpackages(path: Path):
    """定义层（扩展作者继承的基类）不得在运行期依赖 Runtime/ 与 Market/，避免导入环。"""
    offenders = [module for module in _iter_imported_modules(path) if _matches(module, FORBIDDEN_FOR_DEFINITIONS)]
    assert not offenders, f'{path.relative_to(CORE_DIR.parent)} must not import subpackages at runtime: {offenders}'


@pytest.mark.parametrize(
    'path',
    [path for path in (EXTENSION_DIR / 'Runtime').rglob('*.py') if '__pycache__' not in path.parts],
    ids=lambda path: path.name,
)
def test_runtime_does_not_import_market(path: Path):
    """Runtime/ 不得依赖 Market/（方向单向：定义层 → Runtime → Market）。"""
    offenders = [module for module in _iter_imported_modules(path) if _matches(module, ('Core.Extension.Market',))]
    assert not offenders, f'{path.relative_to(CORE_DIR.parent)} must not import Market: {offenders}'


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
        offenders.extend(module for module in _iter_imported_modules(path) if _matches(module, forbidden))
    assert not offenders, f'Core.I18n must not import Core business modules: {offenders}'


def test_manifest_does_not_import_extension():
    """Manifest 为清单层，不得反向导入 Extension（避免 Extension↔Manifest 循环）。"""
    offenders = [
        module for module in _iter_imported_modules(EXTENSION_DIR / 'Manifest.py') if module.endswith('.Extension')
    ]
    assert not offenders, f'Core.Extension.Manifest must not import Extension: {offenders}'
