# in development
import os
import random
import time
from datetime import datetime

from nonebot import logger, on_notice, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    LuckyKingNotifyEvent,
    Message,
    MessageSegment,
    PokeNotifyEvent,
)
from nonebot.typing import T_State

from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot.rule import to_me

from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period

getPrevMsg = on_command("getPrevMsg", rule=to_me(), priority=1, block=True)

@getPrevMsg.handle()
async def getPrevMsg_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not event.group_id in Config.group_whitelist:
        getPrevMsg.skip()
        return


