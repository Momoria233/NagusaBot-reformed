import sys
from datetime import datetime
import time
from collections import OrderedDict
import pytz
from nonebot import logger, get_bot
from nonebot.exception import FinishedException
from src.common.config import global_config
from typing import Tuple, Optional, Any
from nonebot.adapters.onebot.v11 import Bot

class _LRUTTLCache:
    def __init__(self, maxsize: int, ttl_seconds: Optional[int] = None):
        self._maxsize = max(0, int(maxsize))
        self._ttl_seconds = int(ttl_seconds) if ttl_seconds is not None else None
        self._store: "OrderedDict[Any, Tuple[Any, Optional[float]]]" = OrderedDict()

    def get(self, key: Any) -> Optional[Any]:
        if self._maxsize <= 0:
            return None
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key, last=True)
        return value

    def set(self, key: Any, value: Any) -> None:
        if self._maxsize <= 0:
            return
        expires_at = (
            time.monotonic() + self._ttl_seconds
            if self._ttl_seconds is not None and self._ttl_seconds > 0
            else None
        )
        if key in self._store:
            self._store.pop(key, None)
        self._store[key] = (value, expires_at)
        self._store.move_to_end(key, last=True)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

_group_name_cache = _LRUTTLCache(maxsize=2048, ttl_seconds=24 * 60 * 60)
_user_card_cache = _LRUTTLCache(maxsize=8192, ttl_seconds=6 * 60 * 60)
_stranger_name_cache = _LRUTTLCache(maxsize=8192, ttl_seconds=24 * 60 * 60)

async def get_group_name(bot: Bot, group_id: int) -> str:
    name = _group_name_cache.get(group_id)
    if name:
        return name
    try:
        info = await bot.get_group_info(group_id=group_id)
        name = info.get("group_name") or str(group_id)
        _group_name_cache.set(group_id, name)
        return name
    except Exception:
        return str(group_id)

async def get_user_display_name(bot: Bot, user_id: int, group_id: Optional[int] = None) -> str:
    if group_id is not None:
        key = (group_id, user_id)
        name = _user_card_cache.get(key)
        if name:
            return name
        try:
            info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
            name = info.get("card") or info.get("nickname") or str(user_id)
            _user_card_cache.set(key, name)
            return name
        except Exception:
            pass
    name = _stranger_name_cache.get(user_id)
    if name:
        return name
    try:
        info = await bot.get_stranger_info(user_id=user_id)
        name = info.get("nickname") or str(user_id)
        _stranger_name_cache.set(user_id, name)
        return name
    except Exception:
        return str(user_id)

async def error_report_sink(message):
    """
    Loguru sink that sends error logs to the Superuser.
    """
    record = message.record
    exception = record["exception"]
    
    # Filter out non-critical exceptions
    if exception:
        exc_type = exception.type
        # Ignore FinishedException (Control flow)
        if issubclass(exc_type, FinishedException):
            return

    # Format the error message
    err_msg = f"⚠️ [Error Report]\n{record['message']}\n"
    if exception:
        err_msg += f"{exception.type.__name__}: {exception.value}"

    try:
        bot = get_bot()
        # Use config for Superuser ID
        await bot.send_private_msg(user_id=global_config.superuser_id, message=err_msg)
    except Exception:
        pass

def setup_logger():
    """
    Configure Loguru logger with file output and admin reporting.
    """
    # Create logs directory
    import os
    if not os.path.exists("./logs"):
        os.makedirs("./logs")

    timestamp = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d_%H-%M-%S")
    
    # File Sinks
    logger.add(f'./logs/{timestamp}.log', level="DEBUG", rotation="10 MB")
    logger.add(f'./logs/{timestamp}.error', level="ERROR", rotation="10 MB")
    
    # Admin Report Sink (Async)
    logger.add(error_report_sink, level="ERROR")

