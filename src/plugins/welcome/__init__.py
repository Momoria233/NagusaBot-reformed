import re

from nonebot import logger, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupIncreaseNoticeEvent,
    Message,
    MessageSegment,
)
from nonebot.typing import T_State
import os
from .config import Config

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
NewWelcome = on_notice()


@NewWelcome.handle()
async def welcoming(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    if not event.group_id in Config.welcome_message:
        await NewWelcome.finish()
    logger.info(f"match group id {event.group_id}")
    parts = re.split(r"\{([^}]+)\}", Config.welcome_message[event.group_id])
    message_list: list[MessageSegment] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part:
                message_list.append(MessageSegment.text(part))
        else:
            match part:
                case "at":
                    message_list.append(MessageSegment.at(event.get_user_id()))
                case str() as string if re.match(r"img:(.*)", string):
                    logger.info(re.match(r"img:(.*)", string).group(1))
                    logger.info(os.path.join(assets_dir, re.match(r"img:(.*)", string).group(1)))
                    message_list.append(MessageSegment.image(os.path.join(assets_dir,re.match(r"img:(.*)", string).group(1))))

    await NewWelcome.finish(Message(message_list))
