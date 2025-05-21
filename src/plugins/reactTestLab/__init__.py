import os
import random
import time
from datetime import datetime
import json
from datetime import datetime, timedelta, timezone

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

tz = timezone(timedelta(hours=8))
noticeTest = on_regex(r"广告请注意时间段$")
@noticeTest.handle()
async def handle_notice(bot: Bot, event: GroupMessageEvent, state: T_State):
    now = datetime.now(tz)
    if not event.reply or now.hour == 12 :
        return
    logger.info(event.get_message())
    logger.info(event.reply.message_id)
    logger.info(event.message_id)
    await bot.delete_msg(message_id=event.reply.message_id)
    repmsg = await bot.get_msg(message_id=event.reply.message_id)
    msg = await bot.get_msg(message_id=event.message_id)
    logger.info(repmsg)
    logger.info(msg)
    # logger.warning(f"[reactTestLab] New Event Received")
    await noticeTest.finish()