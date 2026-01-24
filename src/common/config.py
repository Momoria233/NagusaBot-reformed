IS_PYDANTIC_V2 = False
try:
    from pydantic_settings import BaseSettings
    try:
        from pydantic_settings import SettingsConfigDict
    except Exception:
        SettingsConfigDict = None
    IS_PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings
    SettingsConfigDict = None

from pydantic import Field
try:
    from pydantic import field_validator
except Exception:
    field_validator = None

if not IS_PYDANTIC_V2:
    try:
        from pydantic.v1 import validator
    except ImportError:
        try:
            from pydantic import validator
        except ImportError:
            pass

from typing import Set, Optional, Any
import json
from nonebot import get_driver

def _parse_int_set(v: Any) -> Set[int]:
    if v is None:
        return set()
    if isinstance(v, set):
        return set(int(x) for x in v)
    if isinstance(v, (list, tuple)):
        return set(int(x) for x in v)
    if isinstance(v, int):
        return {int(v)}
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return set()
        parsed = None
        try:
            parsed = json.loads(s)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return set(int(x) for x in parsed)
        if isinstance(parsed, int):
            return {int(parsed)}
        parts = [p for p in s.replace("\n", ",").replace(" ", ",").split(",") if p]
        return set(int(p) for p in parts if p.isdigit())
    return set()

class Config(BaseSettings):
    # System Config
    superuser_id: int = Field(default=2447209382, description="Admin QQ ID")
    bot_admins: Set[int] = Field(default_factory=set, description="Bot-level admins")
    environment: str = Field(default="dev", description="dev or prod")
    
    # Database
    db_url_dev: str = "sqlite://db.sqlite3"
    db_url_prod: str = "sqlite://db.sqlite3"
    
    # Third Party Keys (Load from .env)
    bilibili_cookie: Optional[str] = Field(None, env="BILIBILI_COOKIE")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_base_url: str = "https://api.openai.com/v1"

    # Plugin Specific Configs
    total_react_cooldown: int = 30
    total_react_whitelist: Set[str] = {"2447209382"}
    
    # Auto Group Acception
    auto_group_manual_approve_list: Set[int] = set()

    # JM Plugin
    jm_download_thread: int = 16
    jm_allow_private: bool = True
    jm_user_whitelist: Set[int] = {2447209382, 3343752977}

    # UniRecall Plugin
    log_group_id: Optional[int] = 1036382420
    backup_group_id: Optional[int] = 1048079889
    uni_recall_trusted_users: Set[int] = {2447209382, 2743654437}

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(extra="ignore", env_file=(".env.prod", ".env"), env_file_encoding="utf-8")
    else:
        class Config:
            extra = "ignore"
            env_file = (".env.prod", ".env")
            env_file_encoding = "utf-8"

    if IS_PYDANTIC_V2:
        @field_validator("bot_admins", mode="before")
        @classmethod
        def _parse_bot_admins(cls, v: Any):
            # print(f"DEBUG: validator (v2) called with {v} type {type(v)}")
            return _parse_int_set(v)
    else:
        @validator("bot_admins", pre=True, always=True)
        def _parse_bot_admins(cls, v: Any):
            # print(f"DEBUG: validator (v1) called with {v} type {type(v)}")
            return _parse_int_set(v)

# Global Config Instance
_driver_config = get_driver().config.dict()
_bot_admins = _parse_int_set(_driver_config.get("bot_admins"))

print(f"DEBUG: IS_PYDANTIC_V2={IS_PYDANTIC_V2}")
print(f"DEBUG: _driver_config bot_admins raw: {_driver_config.get('bot_admins')}")
print(f"DEBUG: parsed _bot_admins: {_bot_admins}, type: {type(_bot_admins)}")

if _bot_admins:
    _driver_config["bot_admins"] = _bot_admins
else:
    _driver_config.pop("bot_admins", None)

print(f"DEBUG: final _driver_config keys: {_driver_config.keys()}")
if "bot_admins" in _driver_config:
    print(f"DEBUG: final bot_admins in dict: {_driver_config['bot_admins']} type: {type(_driver_config['bot_admins'])}")

global_config = Config(**_driver_config)
