import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.common.resource import resource_manager


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    default_open: bool
    description: str = ""


@dataclass(frozen=True)
class PermissionDecision:
    enabled: bool
    source: str
    default_open: bool


class PermissionManager:
    def __init__(self):
        self._registry: Dict[str, Dict[str, object]] = {}

    def register(self, plugin_reg_name: str, plugin_real_name: str, features: List[FeatureSpec], group_customize: bool) -> None:
        feature_map = {
            f.name: {
                "default_open": bool(f.default_open),
                "description": str(f.description),
            }
            for f in features
        }
        self._registry[plugin_reg_name] = {
            "group_customize": bool(group_customize),
            "features": feature_map,
            "real_name": str(plugin_real_name),
        }

    def list_plugins(self) -> List[str]:
        return sorted(self._registry.keys())

    def list_features(self, plugin_reg_name: str) -> Tuple[str, List[Tuple[str, str]]]:
        plugin = self._registry.get(plugin_reg_name)
        if plugin is None:
            return "", []
        real_name = str(plugin.get("real_name") or plugin_reg_name)
        features = plugin.get("features", {}) or {}
        items: List[Tuple[str, str]] = []
        for name in sorted(features.keys()):
            meta = features.get(name)
            if isinstance(meta, dict):
                desc = str(meta.get("description") or "")
            else:
                desc = ""
            items.append((name, desc))
        return real_name, items

    def get_feature_default(self, plugin_reg_name: str, feature_name: str) -> bool:
        plugin = self._registry.get(plugin_reg_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_reg_name} is not registered")
        features = plugin.get("features", {})
        if feature_name not in features:
            raise ValueError(f"Feature {feature_name} is not registered for plugin {plugin_reg_name}")
        meta = features.get(feature_name)
        if isinstance(meta, dict):
            return bool(meta.get("default_open"))
        return bool(meta)

    def is_group_customize_allowed(self, plugin_reg_name: str) -> bool:
        plugin = self._registry.get(plugin_reg_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_reg_name} is not registered")
        return bool(plugin.get("group_customize", False))

    def get_decision(
        self,
        plugin_reg_name: str,
        feature_name: str,
        group_id: Optional[int],
        user_id: Optional[int] = None,
    ) -> PermissionDecision:
        default_open = self.get_feature_default(plugin_reg_name, feature_name)
        if group_id is None or not self.is_group_customize_allowed(plugin_reg_name):
            return PermissionDecision(enabled=default_open, source="default", default_open=default_open)
        override = _read_feature_override(plugin_reg_name, group_id, feature_name)
        if not override:
            return PermissionDecision(enabled=default_open, source="default", default_open=default_open)
        state = override.get("state")
        enabled = default_open
        source = "default"
        if state == "allow":
            enabled = True
            source = "state"
        elif state == "deny":
            enabled = False
            source = "state"
        if user_id is not None:
            whitelist = _normalize_id_list(override.get("whitelist"))
            blacklist = _normalize_id_list(override.get("blacklist"))
            user_id_str = str(user_id)
            if whitelist and (user_id in whitelist or user_id_str in whitelist):
                enabled = True
                source = "whitelist"
            if blacklist and (user_id in blacklist or user_id_str in blacklist):
                enabled = False
                source = "blacklist"
        return PermissionDecision(enabled=enabled, source=source, default_open=default_open)

    def is_enabled(
        self,
        plugin_reg_name: str,
        feature_name: str,
        group_id: Optional[int],
        user_id: Optional[int] = None,
    ) -> bool:
        return self.get_decision(plugin_reg_name, feature_name, group_id, user_id).enabled

    def set_feature_state(self, plugin_reg_name: str, feature_name: str, group_id: int, enabled: bool) -> None:
        if group_id is None:
            return
        self.get_feature_default(plugin_reg_name, feature_name)
        data = _read_group_config(plugin_reg_name, group_id)
        permissions = data.get("permissions")
        if not isinstance(permissions, dict):
            permissions = {}
        features = permissions.get("features")
        if not isinstance(features, dict):
            features = {}
        feature = features.get(feature_name)
        if not isinstance(feature, dict):
            feature = {}
        feature["state"] = "allow" if enabled else "deny"
        features[feature_name] = feature
        permissions["features"] = features
        data["permissions"] = permissions
        _write_group_config(plugin_reg_name, group_id, data)


def _normalize_id_list(values: object) -> List[object]:
    if not isinstance(values, list):
        return []
    return values


def _get_group_config_path(plugin_reg_name: str, group_id: int) -> Path:
    data_root = resource_manager.data_root
    return data_root / "config" / plugin_reg_name / f"{int(group_id)}.json"


def _read_group_config(plugin_reg_name: str, group_id: int) -> Dict[str, object]:
    path = _get_group_config_path(plugin_reg_name, group_id)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f) or {}
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_group_config(plugin_reg_name: str, group_id: int, data: Dict[str, object]) -> None:
    path = _get_group_config_path(plugin_reg_name, group_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_feature_override(plugin_reg_name: str, group_id: int, feature_name: str) -> Dict[str, object]:
    data = _read_group_config(plugin_reg_name, group_id)
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict):
        return {}
    features = permissions.get("features", {})
    if not isinstance(features, dict):
        return {}
    feature = features.get(feature_name, {})
    return feature if isinstance(feature, dict) else {}


permission_manager = PermissionManager()
