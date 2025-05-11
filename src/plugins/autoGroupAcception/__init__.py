from nonebot import logger, on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent
from nonebot.typing import T_State

from .config import Config

import json, os

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def check_stu_name(input_name):
    with open(os.path.join(assets_dir,"replacement.json"), 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                if (input_name == item.get("FullName") or
                    input_name == item.get("FamilyName") or
                    input_name == item.get("PersonalName")):
                    return True
            return False

GroupRequest = on_notice()
@GroupRequest.handle()
async def handle_group_request(bot:Bot, event: GroupRequestEvent):
    logger.info(f"[autoGroupAcception] Group {event.group_id} request from {event.user_id}")
    if not event.group_id in Config.group_whitelist:
        logger.info(f"[autoGroupAcception] Group {event.group_id} not in whitelist")
        await GroupRequest.finish()
    logger.info(event.comment)
    answer = event.comment.split("答案：", 1)[1] if "答案：" in event.comment else ""
    logger.info(answer)
    if check_stu_name(event.comment):
        event.approve()
        await GroupRequest.finish()
    else:
        await GroupRequest.finish()