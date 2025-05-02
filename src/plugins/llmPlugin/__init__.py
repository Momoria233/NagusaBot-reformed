import os
import random
import time
from datetime import datetime

import nonebot
from nonebot import logger, on_notice, on_regex, on_command, on_message
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
from .llmResp import get_yulu_response
from .config import Config
import re

cooldown_tracker = {}
cooldown_period = Config.cooldown_period

MAX_HISTORY = 50

group_message_history: dict[int, list[str]] = {}

def get_last_group_messages(group_id: int, count: int = 5) -> list[str]:
    messages = group_message_history.get(group_id, [])
    return messages[-count:] if messages else []

record_message = on_message(priority=99, block=False)

@record_message.handle()
async def record_message_handle(event: GroupMessageEvent):
    group_id = event.group_id
    message = str(event.get_message())

    if "[CQ:image" in message or message.startswith("[CQ:mface"):
        return

    match = re.search(r']\s*(.+)', message)
    if match:
        message = match.group(1).strip()

    if group_id not in group_message_history:
        group_message_history[group_id] = []

    group_message_history[group_id].append(message)

    # 保持最大长度
    if len(group_message_history[group_id]) > MAX_HISTORY:
        group_message_history[group_id].pop(0)

last_cmd = on_command("rev",priority=5, block=True)

@last_cmd.handle()
async def handle_last_command(bot: Bot, event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    group_id = event.group_id
    # if not event.user_id in Config.usr_whitelist:
    #     await matcher.finish()

    try:
        n = int(str(args).strip()) if str(args).strip() else 5
    except ValueError:
        await bot.call_api("send_msg",messagetype="private",user_id=2447209382, message={"type": "text", "data": {"text": "格式错误，请输入 /last [数字]"}})
        await matcher.finish()

    last_messages = get_last_group_messages(group_id, n)

    if not last_messages:
        await bot.call_api("send_msg",messagetype="private",user_id=2447209382, message={"type": "text", "data": {"text": "暂无记录"}})
        await matcher.finish()

    output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(last_messages)])
    llmReply = get_yulu_response(output)
    await bot.call_api("send_msg",messagetype="private",user_id=2447209382, message={"type": "text", "data": {"text": f"{output}"}})
    try:
        await matcher.finish(message=Message(MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"yulu/{llmReply}"))))
    except nonebot.exception.FinishedException:
        pass
    except Exception as e:
        await bot.call_api("send_msg",messagetype="private",user_id=2447209382, message={"type": "text", "data": {"text": f"{e}"}})
        logger.error(f"Error sending image: {e}")
        await matcher.finish()