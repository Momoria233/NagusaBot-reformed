import os
import random
import time
from datetime import datetime
import json


from nonebot import logger, on_notice, on_regex, on_command, on_message, on_request
import nonebot.exception
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    LuckyKingNotifyEvent,
    Message,
    MessageSegment,
    PokeNotifyEvent,
    GroupRequestEvent,
    FriendRequestEvent
)
from nonebot.typing import T_State
from nonebot.params import CommandArg

from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period

noticeTest = on_notice()

@noticeTest.handle()
async def handle_notice(bot: Bot):
    logger.warning(f"[reactTestLab] New Event Received")
    await noticeTest.finish()