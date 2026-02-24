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

# Import PermissionManager
from src.common.permission_manager import FeatureSpec, permission_manager

PLUGIN_REG_NAME = "Legacy-Help"
PLUGIN_REAL_NAME = "帮助"
FEATURE_HELP = "help"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_HELP, default_open=True, description="at bot发送/help可以查看当前群内可使用的功能列表。")],
    group_customize=True,
)

groupfwdmsg = on_command("help",aliases={"帮助"})

@groupfwdmsg.handle()
async def groupfwdmsg_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_HELP, event.group_id, event.user_id):
        await groupfwdmsg.finish("功能未开启")
    helpMsg = {
        "group_id": event.group_id,
        "messages": []
    }
    helpMsg["messages"].append({
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": "老师好！欢迎使用名草Bot。\n本项目在功能上少许参考了@百合园圣娅ᴮᴼᵀ，并开源于GitHub。"
                }
            })
    helpMsg["messages"].append({
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": "如果您有任何意见、建议或者想法可以直接私信Bot，\n虽然不一定能及时回复但一定都会看的。"
                }
            })
    helpMsg["messages"].append({
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": "--==功能列表==--"
                }
            })
    for plugin_name in permission_manager.list_plugins():
        real_name, feature_items = permission_manager.list_features(plugin_name)
        for feature_name, feature_desc in feature_items:
            decision = permission_manager.get_decision(
                plugin_name, feature_name, event.group_id, event.user_id
            )
            if not decision.enabled:
                continue
            desc = f"{feature_desc}" if feature_desc else ""
            node_content = [{
                "type": "text",
                "data": {"text": f"{feature_name}：\n{desc}"}
            }]
            helpMsg["messages"].append({
                "type": "node",
                "data": {
                    "user_id": "3856749436",
                    "nickname": "名草Bot",
                    "content": node_content
                }
            })

    if not helpMsg["messages"]:
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

    logger.info(f"Sending help message to group {event.group_id}")

    try:
        await bot.call_api("send_group_forward_msg", **helpMsg)
    except Exception as e:
        logger.error(f"Failed to send help message: {e}")
