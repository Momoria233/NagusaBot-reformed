from nonebot import logger, on_request
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent, PrivateMessageEvent
from nonebot.typing import T_State
from nonebot import on_message
import asyncio

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
            return False

async def check_manual_approve(bot: Bot, event: GroupRequestEvent,type: str,answer: str):
    if type == "autoMatchFailed":
        msg = (f"Group {event.group_id} request from {event.user_id} 匹配失败。 \n申请提示词: {answer}，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=2447209382, message=msg)
    elif type == "manualApprove":
        msg = (f"Group {event.group_id} request from {event.user_id} 需要人工审核，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=2447209382, message=msg)
    else:
        return False
    key = f"{event.group_id}_{event.user_id}"
    pending_requests[key] = (bot, event)
    try:
        result = await asyncio.wait_for(wait_for_reply(key), timeout=300)
        if result == "是":
            await event.approve(bot)
            await bot.send_private_msg(user_id=2447209382, message="已通过。")
        elif result == "否":
            await event.reject(bot)
            await bot.send_private_msg(user_id=2447209382, message="已拒绝。")
        else:
            await bot.send_private_msg(user_id=2447209382, message=f"未知回复，已结束处理。回复：{result}。")
    except asyncio.TimeoutError:
        await bot.send_private_msg(user_id=2447209382, message="5分钟超时，已结束处理。")
    finally:
        pending_requests.pop(key, None)

pending_requests = {}

GroupRequest = on_request(priority=1)
@GroupRequest.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent):
    logger.info(f"Group {event.group_id} request from {event.user_id}")
    if not event.group_id in Config.group_whitelist:
        logger.info(f"Group {event.group_id} not in whitelist")
        await GroupRequest.finish()
    logger.info(event.comment)
    answer = event.comment.split("答案：", 1)[1] if "答案：" in event.comment else ""
    logger.info(answer)
    if event.group_id in Config.manual_approve_list:
        logger.info(f"group {event.group_id} in manual approve list")
        await check_manual_approve(bot, event, "manualApprove")
        await GroupRequest.finish()
    if check_stu_name(answer):
        await event.approve(bot)
        msg = f"Group {event.group_id} request from {event.user_id} approved"
        logger.info(msg)
        await bot.send_private_msg(user_id=2447209382, message=msg)
        await GroupRequest.finish()
    else:
        logger.info(f"Group {event.group_id} request from {event.user_id} auto match failed")
        await check_manual_approve(bot, event, type="autoMatchFailed",answer=answer)
        await GroupRequest.finish()

async def wait_for_reply(key):
    fut = asyncio.get_event_loop().create_future()
    pending_requests[key] = fut
    return await fut

private_msg = on_message(priority=1)
@private_msg.handle()
async def handle_private_msg(bot: Bot, event: PrivateMessageEvent):
    if event.user_id != 2447209382:
        return
    for key, fut in list(pending_requests.items()):
        if isinstance(fut, asyncio.Future) and not fut.done():
            if event.message.extract_plain_text().strip() in ["是", "否"]:
                fut.set_result(event.message.extract_plain_text().strip())
                await private_msg.finish()