from nonebot import logger, on_request
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent
from nonebot.typing import T_State

from .config import Config

import json, os

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

with open(os.path.join(assets_dir,"replacement.json"), 'r', encoding='utf-8') as f:
            checkData = json.load(f)

def check_stu_name(input_name):
            for item in checkData:
                if (input_name == item.get("FullName") or
                    input_name == item.get("FamilyName") or
                    input_name == item.get("PersonalName") or
                    item.get("FullName") in input_name):
                    return True
                # else:
                #     logger.warning(f"{input_name} not in {item.get('FullName')}, {item.get('FamilyName')}, {item.get('PersonalName')}")
            return False

GroupRequest = on_request(priority=1)
@GroupRequest.handle()
async def handle_group_request(bot:Bot, event: GroupRequestEvent):
    logger.info(f"[autoGroupAcception] Group {event.group_id} request from {event.user_id}")
    if not event.group_id in Config.group_whitelist:
        logger.info(f"[autoGroupAcception] Group {event.group_id} not in whitelist")
        await GroupRequest.finish()
    logger.info(event.comment)
    answer = event.comment.split("答案：", 1)[1] if "答案：" in event.comment else ""
    logger.info(answer)
    if check_stu_name(answer):
        await event.approve(bot)
        msg = f"[autoGroupAcception] Group {event.group_id} request from {event.user_id} approved"
        logger.info(msg)
        bot.send_private_msg(user_id=2447209382,message=msg)
        await GroupRequest.finish()
    else:
        msg = f"[autoGroupAcception] Group {event.group_id} request from {event.user_id} rejected, answer: {answer}"
        logger.info(msg)
        bot.send_private_msg(user_id=2447209382,message=msg)
        await GroupRequest.finish()