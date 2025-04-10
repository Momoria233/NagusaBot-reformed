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

from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period


def usr_cd_check(user_id: str) -> bool:
    current_time = time.time()
    if user_id in Config.cooldown_whitelist:
        return True
    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            return False
    cooldown_tracker[user_id] = current_time
    return True

he = on_regex(pattern=r"^我超.*盒$", priority=1)
@he.handle()
async def he_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    at = MessageSegment.at(event.get_user_id())
    try:
        await he.finish(message=Message([at,MessageSegment.record(file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "he.mp3"))]))
    except Exception as e:
        logger.error(e)

MAX_HISTORY = 50

# 消息缓存：{ group_id: [msg1, msg2, ...] }
group_message_history: dict[int, list[str]] = {}

def get_last_group_messages(group_id: int, count: int = 5) -> list[str]:
    messages = group_message_history.get(group_id, [])
    return messages[-count:] if messages else []

# 监听所有群消息，缓存入 group_message_history
record_message = on_message(priority=99, block=False)

@record_message.handle()
async def record_message_handle(event: GroupMessageEvent):
    group_id = event.group_id
    message = str(event.get_message())

    if group_id not in group_message_history:
        group_message_history[group_id] = []

    group_message_history[group_id].append(message)

    # 保持最大长度
    if len(group_message_history[group_id]) > MAX_HISTORY:
        group_message_history[group_id].pop(0)

# 用户触发指令查看历史记录：/last [n]
last_cmd = on_command("last", aliases={"历史", "recent"})

@last_cmd.handle()
async def handle_last_command(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    group_id = event.group_id

    try:
        # 用户输入 /last 10
        n = int(str(args).strip()) if str(args).strip() else 5
    except ValueError:
        await matcher.finish("格式错误，请输入 /last [数字]")

    last_messages = get_last_group_messages(group_id, n)

    if not last_messages:
        await matcher.finish("暂无记录~")

    # 格式化输出
    output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(last_messages)])
    await matcher.finish(output)