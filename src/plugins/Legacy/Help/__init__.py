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

# Import FeatureManager
from src.common.feature_manager import feature_manager

# Register /help feature
feature_manager.register("/help", ": \nat bot发送/help可以查看当前群内可使用的功能列表。")

groupfwdmsg = on_command("help",aliases={"帮助"})

@groupfwdmsg.handle()
async def groupfwdmsg_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_id = str(event.group_id)
    
    # Get enabled features
    enabled_features = feature_manager.get_group_features(group_id)
    
    helpMsg = {
        "group_id": event.group_id,
        "messages": []
    }

    if not enabled_features:
        # No features enabled
        node_content = [{
            "type": "text",
            "data": {"text": "本群目前没有启用任何功能"}
        }]
        helpMsg["messages"].append({
            "type": "node",
            "data": {
                "user_id": "3856749436",
                "nickname": "名草Bot",
                "content": node_content
            }
        })
    else:
        for feature, description in enabled_features.items():
            node_content = [{
                "type": "text",
                "data": {"text": f"{feature} {description}"}
            }]
            helpMsg["messages"].append({
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": node_content
                }
            })

    logger.info(f"Sending help message to group {group_id}")

    try:
        await bot.call_api("send_group_forward_msg", **helpMsg)
    except Exception as e:
        logger.error(f"Failed to send help message: {e}")
