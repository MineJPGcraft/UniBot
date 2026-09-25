"""
NoneBot DRIVER 字段的解析与维护工具。

负责在安装/卸载适配器时，自动维护 `.env` 中 DRIVER 的额外驱动项。

本模块**只计算**驱动对应的底层依赖包（`driver_packages`）并维护 `.env`，
不直接改写 `pyproject.toml`：依赖的新增/移除由调用方提交任务中心，
经 `uv add` / `uv remove` 完成（见 `Scripts/Api/Config/Router.py`）。
"""

from Scripts.Managers import config_manager

from .Adapters import ADAPTER_DRIVERS, BASE_DRIVER

# NoneBot 内置驱动标记（`~` 为 nonebot.drivers. 缩写）对应的底层依赖包。
# BASE_DRIVER（~fastapi）由 nonebot2[fastapi] 自带，无需额外声明。
DRIVER_PACKAGES: dict[str, str] = {
    '~httpx': 'httpx',
    '~websockets': 'websockets',
    '~aiohttp': 'aiohttp',
    '~quart': 'quart',
}


def get_required_drivers(module_name: str) -> list[str]:
    """获取指定适配器模块所需的额外驱动列表。"""
    return ADAPTER_DRIVERS.get(module_name, [])


def get_driver_package(driver: str) -> str | None:
    """返回驱动标记对应的底层依赖包名，若无需显式声明则返回 None。"""
    return DRIVER_PACKAGES.get(driver)


def driver_packages(drivers: list[str]) -> list[str]:
    """
    把驱动标记映射为底层依赖包名（跳过无需显式声明的，如 BASE_DRIVER）。

    返回的包名交由任务中心用 `uv add` 写入 `project.dependencies`。
    """
    packages: list[str] = []
    for driver in drivers:
        package = get_driver_package(driver)
        if package and package not in packages:
            packages.append(package)
    return packages


def parse_driver(driver_value: str | list | None) -> list[str]:
    """将 DRIVER 配置解析为驱动列表。"""
    if not driver_value:
        return [BASE_DRIVER]
    items = driver_value if isinstance(driver_value, list) else driver_value.split('+')
    drivers = [stripped for item in items if (stripped := item.strip())]
    if BASE_DRIVER not in drivers:
        drivers.append(BASE_DRIVER)
    return drivers


def format_driver(drivers: list[str]) -> str:
    """将驱动列表格式化为 DRIVER 字符串。"""
    return '+'.join(drivers)


def merge_driver(required_drivers: list[str]) -> tuple[str, list[str]]:
    """
    将所需驱动合并到当前 DRIVER 配置中。
        返回 (新 DRIVER 字符串, 新增的驱动列表)。

    仅写 `.env`；新增驱动对应的底层依赖包由调用方取 `driver_packages(added)`
    走 `uv add`，避免绕过 uv 直接改写 pyproject.toml。
    """
    current = config_manager.environment.get('DRIVER', BASE_DRIVER)
    current_drivers = parse_driver(current)
    added = [driver for driver in required_drivers if driver not in current_drivers]
    if not added:
        return current, []
    new_drivers = current_drivers + added
    new_value = format_driver(new_drivers)
    config_manager.update_env({'DRIVER': new_value})
    return new_value, added


def shrink_driver(redundant_drivers: list[str]) -> tuple[str, list[str]]:
    """
    从当前 DRIVER 配置中移除多余驱动（前提：剩余已注册适配器都不再需要）。
        返回 (新 DRIVER 字符串, 实际移除的驱动列表)。

    只动 `.env` 的 DRIVER，**不**移除底层依赖包：httpx / websockets 等常被
    适配器包本身及其它依赖引用，误删会导致环境不可用。
    """
    current = config_manager.environment.get('DRIVER', BASE_DRIVER)
    current_drivers = parse_driver(current)
    removed = [driver for driver in redundant_drivers if driver in current_drivers]
    if not removed:
        return current, []
    new_drivers = [driver for driver in current_drivers if driver not in removed]
    if BASE_DRIVER not in new_drivers:
        new_drivers.append(BASE_DRIVER)
    new_value = format_driver(new_drivers)
    config_manager.update_env({'DRIVER': new_value})
    return new_value, removed


def compute_redundant_drivers(uninstalling_module: str) -> list[str]:
    """
    计算卸载某适配器后可以移除的驱动：
        即该适配器需要、但其他仍注册的适配器都不再需要的驱动。
    """
    target_drivers = set(get_required_drivers(uninstalling_module))
    if not target_drivers:
        return []
    project_data = config_manager.read_pyproject()
    registered_modules: set[str] = set()
    for adapter in project_data.get('tool', {}).get('nonebot', {}).get('adapters', []):
        if not isinstance(adapter, dict):
            continue
        module_name = adapter.get('module_name')
        if not isinstance(module_name, str) or not module_name or module_name == uninstalling_module:
            continue
        registered_modules.add(module_name)
    still_needed: set[str] = set()
    for module_name in registered_modules:
        still_needed.update(get_required_drivers(module_name))
    return sorted(target_drivers - still_needed)
