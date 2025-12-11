from nonebot import logger, on_request, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent, PrivateMessageEvent
from nonebot.typing import T_State
import asyncio
import json
import os
from pathlib import Path

from src.common.feature_manager import feature_manager
from src.common.config import global_config
from src.common.resource import resource_manager

# Register features
feature_manager.register("自动入群申请", ": 对新的入群申请进行正则表达式或json匹配并自动通过，对于未匹配成功的将进入向管理员私信申请手动匹配的功能。")
feature_manager.register("强制人工审核", ": 开启后，该群的所有入群申请都将转为人工审核，忽略自动匹配规则。")

# Load assets
assets_dir = resource_manager.get_bundled_asset_dir(__file__)
replacement_file = assets_dir / "replacement.json"

checkData = []
if replacement_file.exists():
    try:
        with open(replacement_file, 'r', encoding='utf-8') as f:
            checkData = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load replacement.json: {e}")
else:
    logger.warning(f"replacement.json not found at {replacement_file}")

# Global pending requests storage
pending_requests = {}

def check_stu_name(input_name):
    if not input_name:
        return False
    for item in checkData:
        if (input_name == item.get("FullName") or
            input_name == item.get("FamilyName") or
            input_name == item.get("PersonalName") or
            (item.get("FullName") and item.get("FullName") in input_name)):
            return True
    return False

async def wait_for_reply(key):
    fut = asyncio.get_event_loop().create_future()
    # Store the future directly in the dict, or handle structure properly
    # The original code logic was a bit mixed, let's standardize it.
    # We'll store the future itself.
    pending_requests[key] = fut
    return await fut

async def check_manual_approve(bot: Bot, event: GroupRequestEvent, type: str, answer: str):
    superuser = global_config.superuser_id
    
    if type == "autoMatchFailed":
        msg = (f"Group {event.group_id} request from {event.user_id} 匹配失败。 \n申请提示词: {answer}，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=superuser, message=msg)
    elif type == "manualApprove":
        msg = (f"Group {event.group_id} request from {event.user_id} 需要人工审核，\n申请提示词: {answer}，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=superuser, message=msg)
    else:
        return False
        
    key = f"{event.group_id}_{event.user_id}"
    
    try:
        # Wait for the future to be set by the private message handler
        result = await asyncio.wait_for(wait_for_reply(key), timeout=300)
        
        if result == "是":
            await event.approve(bot)
            await bot.send_private_msg(user_id=superuser, message=f"已通过 {event.user_id} 的申请。")
        elif result == "否":
            await event.reject(bot)
            await bot.send_private_msg(user_id=superuser, message=f"已拒绝 {event.user_id} 的申请。")
        else:
            await bot.send_private_msg(user_id=superuser, message=f"未知回复，已结束处理。回复：{result}。")
            
    except asyncio.TimeoutError:
        await bot.send_private_msg(user_id=superuser, message=f"针对 {event.user_id} 的审核超时，已结束处理。")
    finally:
        pending_requests.pop(key, None)

GroupRequest = on_request(priority=1)
@GroupRequest.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent):
    logger.info(f"Group {event.group_id} request from {event.user_id}")
    
    if not feature_manager.is_enabled(event.group_id, "自动入群申请"):
        logger.info(f"Group {event.group_id} feature '自动入群申请' disabled")
        # If feature is disabled, ignore the request (let other plugins handle or default behavior)
        # Usually finish() means "stop processing", but here we might want to just return 
        # to let NoneBot continue? No, finish() stops this matcher.
        await GroupRequest.finish()

    logger.info(event.comment)
    answer = event.comment.split("答案：", 1)[1] if "答案：" in event.comment else event.comment
    logger.info(f"Extracted answer: {answer}")

    # Check for forced manual approve
    if feature_manager.is_enabled(event.group_id, "强制人工审核"):
        logger.info(f"group {event.group_id} has forced manual approve enabled")
        await check_manual_approve(bot, event, type="manualApprove", answer=answer)
        await GroupRequest.finish()

    if check_stu_name(answer):
        await event.approve(bot)
        msg = f"Group {event.group_id} request from {event.user_id} approved (Auto matched)"
        logger.info(msg)
        await bot.send_private_msg(user_id=global_config.superuser_id, message=msg)
        await GroupRequest.finish()
    else:
        logger.info(f"Group {event.group_id} request from {event.user_id} auto match failed")
        await check_manual_approve(bot, event, type="autoMatchFailed", answer=answer)
        await GroupRequest.finish()


private_msg = on_message(priority=1)
@private_msg.handle()
async def handle_private_msg(bot: Bot, event: PrivateMessageEvent):
    if event.user_id != global_config.superuser_id:
        return

    msg_text = event.message.extract_plain_text().strip()
    
    # Check if we have pending requests
    # Note: This logic approves ALL pending requests.
    # This is legacy behavior, preserved for now.
    processed_count = 0
    
    for key, fut in list(pending_requests.items()):
        if isinstance(fut, asyncio.Future) and not fut.done():
            if msg_text in ["是", "否"]:
                fut.set_result(msg_text)
                processed_count += 1
    
    if processed_count > 0:
        await private_msg.finish()
