import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from nonebot import logger
from src.common.models import FeatureSwitch
from tortoise.exceptions import OperationalError

class FeatureManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeatureManager, cls).__new__(cls)
            cls._instance.features = {}  # {name: description}
            # Cache for feature status: {f"{group_id}:{feature_name}": bool}
            # Note: This simple cache might become stale if changed by another process/command.
            # In a real system, you might want a TTL cache or clear it on update.
            cls._instance._cache = {} 
        return cls._instance

    def register(self, name: str, description: str):
        """Register a feature with its description."""
        self.features[name] = description
        logger.info(f"Feature registered: {name}")

    async def set_feature(self, group_id: str, feature_name: str, enabled: bool):
        """Enable or disable a feature for a group (Async, Persisted to DB)."""
        if feature_name not in self.features:
            logger.warning(f"FeatureManager: Attempt to set unknown feature {feature_name}")
            return False
            
        try:
            # Update/Create in DB
            await FeatureSwitch.update_or_create(
                group_id=int(group_id),
                feature_name=feature_name,
                defaults={"is_enabled": enabled}
            )
            # Update Cache
            self._cache[f"{group_id}:{feature_name}"] = enabled
            logger.info(f"FeatureManager: Set {feature_name} to {enabled} for group {group_id}")
            return True
        except Exception as e:
            logger.error(f"FeatureManager: DB Error setting feature: {e}")
            return False

    def is_enabled(self, group_id: str, feature_name: str) -> bool:
        """
        Check if a feature is enabled for a group.
        Note: This method is traditionally synchronous in your code.
        However, DB access is async.
        
        Hybrid Approach:
        1. Check memory cache.
        2. If missing, since we can't await here without changing all caller signatures,
           we must rely on:
           a) Pre-loading all switches at startup (recommended for performance).
           b) Or changing this to `async def is_enabled` (requires refactoring ALL plugins).
           
        For this refactor step, to avoid breaking everything immediately,
        we will assume:
        - Defaults to True (enabled) if not found in cache/DB logic (Optimistic).
        - We need an async method `sync_cache` to load DB into memory periodically or on startup.
        """
        # Return from cache if available
        cache_key = f"{group_id}:{feature_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Default behavior: If we don't know, assume True (or False depending on policy).
        # Most legacy plugins assume enabled unless disabled.
        return True

    async def sync_cache(self):
        """Load all switches from DB to memory."""
        try:
            switches = await FeatureSwitch.all()
            self._cache = {} # Clear old
            for s in switches:
                self._cache[f"{s.group_id}:{s.feature_name}"] = s.is_enabled
            logger.info(f"FeatureManager: Synced {len(switches)} feature switches from DB.")
        except OperationalError:
            # DB might not be ready yet
            pass
        except Exception as e:
            logger.error(f"FeatureManager: Sync cache failed: {e}")

    def get_group_features(self, group_id: str) -> Dict[str, str]:
        """Get list of enabled features for a group."""
        enabled = {}
        for name, desc in self.features.items():
            if self.is_enabled(group_id, name):
                enabled[name] = desc
        return enabled

feature_manager = FeatureManager()
