import os
import random
import time
from datetime import datetime
import json

import nonebot
from nonebot import logger, on_notice, on_regex, on_command, on_message
import nonebot.exception
from nonebot.matcher import Matcher
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

from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period

groupfwdmsg = on_command("help", priority=1)
@groupfwdmsg.handle()
async def groupfwdmsg_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    helpMsg = {
   "group_id": 1040454278,
   "messages": [
      {
         "type": "node",
         "data": {
            "user_id": "3856749436",
            "nickname": "NagusaBot",
            "content": [
               {
                    "type": "text",
                    "data": {
                        "text": "不存在的消息测试"
                    }
                }
            ]
         }
      }
   ]
}
    try:
        await bot.call_api("send_group_forward_msg", **helpMsg)
    except Exception as e:
        logger.error(e)