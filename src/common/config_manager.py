from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Type, Iterable

import yaml
from pydantic import BaseModel

from src.common.resource import resource_manager

try:
    from pydantic import ConfigDict
except Exception:
    ConfigDict = None

try:
    from pydantic_core import core_schema
except Exception:
    core_schema = None


class AssetRef:
    def __init__(self, filename: str):
        self.filename = str(filename)

    @classmethod
    def validate(cls, v: Any):
        if isinstance(v, AssetRef):
            return v
        if isinstance(v, str):
            return AssetRef(v)
        if isinstance(v, dict) and "filename" in v:
            return AssetRef(str(v.get("filename")))
        raise TypeError("Invalid AssetRef")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        if core_schema is None:
            return handler(source_type)
        return core_schema.no_info_plain_validator_function(cls.validate)

    def __repr__(self) -> str:
        return f"AssetRef(filename={self.filename!r})"


class PluginConfig(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="ignore")
    else:
        class Config:
            extra = "ignore"


@dataclass(frozen=True)
class PluginGroupConfigContext:
    values: PluginConfig
    assets: Dict[str, Any]
    meta: Dict[str, Any]


def _model_validate(model_cls: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)
    return model_cls.parse_obj(data)


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(override)
    return merged


def _resolve_asset_value(value: Any, assets_dir: Path) -> Any:
    if value is None:
        return None
    if isinstance(value, AssetRef):
        candidate = assets_dir / value.filename
        return candidate if candidate.exists() else None
    if isinstance(value, str):
        candidate = assets_dir / value
        return candidate if candidate.exists() else None
    if isinstance(value, (list, tuple)):
        return [_resolve_asset_value(v, assets_dir) for v in value]
    return value


def _get_fields(model: BaseModel) -> Iterable[str]:
    if hasattr(model, "model_fields"):
        return model.model_fields.keys()
    return model.__fields__.keys()


class ConfigManager:
    def __init__(self):
        self._registry: Dict[str, Type[PluginConfig]] = {}

    def register(self, plugin_name: str, schema: Type[PluginConfig]) -> None:
        self._registry[plugin_name] = schema

    def get(self, plugin_name: str, group_id: int) -> PluginGroupConfigContext:
        if plugin_name not in self._registry:
            raise ValueError(f"Plugin {plugin_name} is not registered")
        schema = self._registry[plugin_name]
        data_dir = resource_manager.get_data_dir(plugin_name)
        global_config_path = data_dir / "config.yaml"
        group_dir = data_dir / "groups" / str(group_id)
        group_config_path = group_dir / "config.yaml"
        group_assets_dir = group_dir / "assets"

        defaults = _model_dump(schema())
        global_cfg = _read_yaml(global_config_path)
        group_cfg = _read_yaml(group_config_path)

        merged = _merge_dicts(defaults, global_cfg)
        merged = _merge_dicts(merged, group_cfg)

        values = _model_validate(schema, merged)

        assets: Dict[str, Any] = {}
        for field_name in _get_fields(values):
            value = getattr(values, field_name)
            resolved = _resolve_asset_value(value, group_assets_dir)
            if resolved is not value:
                assets[field_name] = resolved

        meta = {
            "plugin": plugin_name,
            "group_id": int(group_id),
            "paths": {
                "global": str(global_config_path),
                "group": str(group_config_path),
            },
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }

        return PluginGroupConfigContext(values=values, assets=assets, meta=meta)

    def update(self, plugin_name: str, group_id: int, values: Dict[str, Any]) -> PluginGroupConfigContext:
        if plugin_name not in self._registry:
            raise ValueError(f"Plugin {plugin_name} is not registered")
        schema = self._registry[plugin_name]
        data_dir = resource_manager.get_data_dir(plugin_name)
        global_config_path = data_dir / "config.yaml"
        group_dir = data_dir / "groups" / str(group_id)
        group_config_path = group_dir / "config.yaml"

        group_cfg = _read_yaml(group_config_path)
        group_cfg = _merge_dicts(group_cfg, values or {})

        defaults = _model_dump(schema())
        global_cfg = _read_yaml(global_config_path)
        merged = _merge_dicts(defaults, global_cfg)
        merged = _merge_dicts(merged, group_cfg)

        validated = _model_validate(schema, merged)
        _write_yaml(group_config_path, group_cfg)

        return self.get(plugin_name, group_id)


config_manager = ConfigManager()
