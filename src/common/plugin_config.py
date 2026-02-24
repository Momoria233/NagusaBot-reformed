import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple

from src.common.resource import resource_manager


def _load_module_from_path(path: Path):
    module_key = f"_plugin_config_{abs(hash(str(path)))}"
    if module_key in sys.modules:
        return sys.modules[module_key]
    spec = importlib.util.spec_from_file_location(module_key, str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load module from path: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = module
    spec.loader.exec_module(module)
    return module


class PluginConfigSource:
    def get_default(self) -> Any:
        raise NotImplementedError()


class PythonFileConfigSource(PluginConfigSource):
    def __init__(self, file_path: Path, default_attr: str = "default_config"):
        self._file_path = Path(file_path)
        self._default_attr = default_attr

    def get_default(self) -> Any:
        module = _load_module_from_path(self._file_path)
        if not hasattr(module, self._default_attr):
            raise ValueError(f"Missing {self._default_attr} in {self._file_path}")
        return getattr(module, self._default_attr)


class PluginConfigPortal:
    def __init__(self):
        self._sources: Dict[str, PluginConfigSource] = {}
        self._allow_group_customize: Dict[str, bool] = {}

    def register_source(self, plugin_name: str, source: PluginConfigSource, allow_group_customize: bool) -> None:
        self._sources[plugin_name] = source
        self._allow_group_customize[plugin_name] = bool(allow_group_customize)

    def get_default(self, plugin_name: str) -> Any:
        source = self._sources.get(plugin_name)
        if source is None:
            raise ValueError(f"Plugin {plugin_name} is not registered")
        return source.get_default()

    def allow_group_customize(self, plugin_name: str) -> bool:
        return bool(self._allow_group_customize.get(plugin_name, False))


plugin_config_portal = PluginConfigPortal()


def _ensure_registered(
    plugin_name: str,
    default_config_path: Path,
    allow_group_customize: bool,
    default_attr: str,
) -> None:
    if plugin_name not in plugin_config_portal._sources:
        plugin_config_portal.register_source(
            plugin_name,
            PythonFileConfigSource(default_config_path, default_attr=default_attr),
            allow_group_customize=allow_group_customize,
        )


def get_default_config(
    plugin_name: str,
    default_config_path: Path,
    allow_group_customize: bool = False,
    default_attr: str = "default_config",
) -> Any:
    _ensure_registered(plugin_name, default_config_path, allow_group_customize, default_attr)
    return plugin_config_portal.get_default(plugin_name)


def _get_group_config_path(plugin_name: str, group_id: int) -> Path:
    data_root = resource_manager.data_root
    return data_root / "config" / plugin_name / f"{int(group_id)}.json"


def _get_group_assets_dir(plugin_name: str, group_id: int) -> Path:
    data_root = resource_manager.data_root
    return data_root / "config" / plugin_name / str(int(group_id)) / "assets"


def get_group_assets_dir(
    plugin_name: str, group_id: Optional[int], create: bool = True
) -> Optional[Path]:
    if group_id is None:
        return None
    path = _get_group_assets_dir(plugin_name, group_id)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _read_group_override(plugin_name: str, group_id: int) -> Dict[str, Any]:
    path = _get_group_config_path(plugin_name, group_id)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f) or {}
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_group_override(plugin_name: str, group_id: int, override: Dict[str, Any]) -> None:
    path = _get_group_config_path(plugin_name, group_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(override, f, ensure_ascii=False, indent=2)


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(override or {})
    return merged


def _diff_dicts(defaults: Dict[str, Any], merged: Dict[str, Any]) -> Dict[str, Any]:
    override: Dict[str, Any] = {}
    for key, value in (merged or {}).items():
        if key not in defaults or defaults.get(key) != value:
            override[key] = value
    return override


def get_group_config(
    plugin_name: str,
    group_id: Optional[int],
    default_config_path: Path,
    allow_group_customize: bool = False,
    default_attr: str = "default_config",
) -> Dict[str, Any]:
    defaults = get_default_config(
        plugin_name,
        default_config_path,
        allow_group_customize=allow_group_customize,
        default_attr=default_attr,
    )
    if group_id is None:
        return dict(defaults)
    if not plugin_config_portal.allow_group_customize(plugin_name):
        return dict(defaults)
    override = _read_group_override(plugin_name, group_id)
    return _merge_dicts(defaults, override)


def update_group_config(
    plugin_name: str,
    group_id: int,
    values: Dict[str, Any],
    default_config_path: Path,
    allow_group_customize: bool = False,
    default_attr: str = "default_config",
) -> Dict[str, Any]:
    defaults = get_default_config(
        plugin_name,
        default_config_path,
        allow_group_customize=allow_group_customize,
        default_attr=default_attr,
    )
    if not plugin_config_portal.allow_group_customize(plugin_name):
        return dict(defaults)
    current_override = _read_group_override(plugin_name, group_id)
    merged_override = _merge_dicts(current_override, values or {})
    merged = _merge_dicts(defaults, merged_override)
    override = _diff_dicts(defaults, merged)
    if override:
        _write_group_override(plugin_name, group_id, override)
    return merged


def get_assets_dir(plugin_file: str, asset_dir_name: str = "assets") -> Path:
    return resource_manager.get_bundled_asset_dir(plugin_file, asset_dir_name=asset_dir_name)


def resolve_assets_map(config: Dict[str, Any], assets_dir: Path) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    for key, value in (config or {}).items():
        resolved_value = resolve_asset_value_with_priority(value, assets_dir, None)
        if resolved_value is not value:
            resolved[key] = resolved_value
    return resolved


def resolve_asset_value_with_priority(
    value: Any, plugin_assets_dir: Path, group_assets_dir: Optional[Path]
) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if group_assets_dir is not None:
            group_candidate = group_assets_dir / value
            if group_candidate.exists():
                return group_candidate
        plugin_candidate = plugin_assets_dir / value
        return plugin_candidate if plugin_candidate.exists() else None
    if isinstance(value, (list, tuple)):
        resolved_list = [
            resolve_asset_value_with_priority(v, plugin_assets_dir, group_assets_dir)
            for v in value
        ]
        resolved_list = [v for v in resolved_list if v is not None]
        return resolved_list or None
    return value


def resolve_assets_map_with_priority(
    config: Dict[str, Any],
    plugin_assets_dir: Path,
    group_assets_dir: Optional[Path],
) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    for key, value in (config or {}).items():
        resolved_value = resolve_asset_value_with_priority(
            value, plugin_assets_dir, group_assets_dir
        )
        if resolved_value is not None and resolved_value is not value:
            resolved[key] = resolved_value
    return resolved


def get_group_config_and_assets(
    plugin_name: str,
    group_id: Optional[int],
    default_config_path: Path,
    plugin_file: str,
    allow_group_customize: bool = False,
    default_attr: str = "default_config",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    config = get_group_config(
        plugin_name,
        group_id,
        default_config_path,
        allow_group_customize=allow_group_customize,
        default_attr=default_attr,
    )
    plugin_assets_dir = get_assets_dir(plugin_file)
    group_assets_dir = get_group_assets_dir(plugin_name, group_id, create=True)
    assets_map = resolve_assets_map_with_priority(
        config, plugin_assets_dir, group_assets_dir
    )
    return config, assets_map
