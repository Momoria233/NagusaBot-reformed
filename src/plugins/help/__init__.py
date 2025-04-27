import os
import random
import time
from datetime import datetime
import json

import nonebot
from nonebot import logger, on_notice, on_regex, on_command, on_message
from nonebot.matcher import Matcher
from nonebot.rule import to_me
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

from .getGroupConfig import *

groupfwdmsg = on_command("help",aliases={"帮助"},priority=1)

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

@groupfwdmsg.handle()
async def groupfwdmsg_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_id = str(event.group_id)
    try:
        with open(os.path.join(assets_dir,"config.json"), "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(e)
        await groupfwdmsg.finish(f"json读取错误：{e}")

    ALL_FEATURES = config.get("all_features", {})

    if group_id not in config:
        enabled_features = list(ALL_FEATURES.keys())
    else:
        group_config = config[group_id]
        ban_list = group_config.get("ban_list", [])
        enabled_features = [feature for feature in ALL_FEATURES if feature not in ban_list]

    if not enabled_features:
        help_text = ["本群目前没有启用任何功能"]
    else:
        help_text = enabled_features

    content = []
    for feature in help_text:
        description = ALL_FEATURES.get(feature, "暂无描述")
        content.append({
            "type": "text",
            "data": {
                "text": f"{feature} {description}"
            }
        })

    helpMsg = {
        "group_id": event.group_id,
        "messages": []
    }

    for feature in help_text:
        node_content = []
        description = ALL_FEATURES.get(feature, "暂无描述")
        node_content.append({
            "type": "text",
            "data": {
                "text": f"{feature} {description}"
            }
        })
        helpMsg["messages"].append(
            {
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": node_content
                }
            },
        )
    logger.info(helpMsg)

    try:
        await bot.call_api("send_group_forward_msg", **helpMsg)
    except Exception as e:
        logger.error(e)