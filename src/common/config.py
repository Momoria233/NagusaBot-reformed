try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings

from pydantic import Field
from typing import Set, Optional
from nonebot import get_driver

class Config(BaseSettings):
    # System Config
    superuser_id: int = Field(default=2447209382, description="Admin QQ ID")
    environment: str = Field(default="dev", description="dev or prod")
    
    # Database
    db_url_dev: str = "sqlite://db.sqlite3"
    db_url_prod: str = "postgresql+asyncpg://user:pass@localhost:5432/nagusabot"
    
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
    backup_group_id: Optional[int] = None
    uni_recall_trusted_users: Set[int] = {2447209382, 2743654437}

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global Config Instance
global_config = Config(**get_driver().config.dict())
