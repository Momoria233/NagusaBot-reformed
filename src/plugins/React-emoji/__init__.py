import os
import random
from nonebot import on_command, on_regex, logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    GroupMessageEvent,
    MessageSegment,
)
from nonebot.params import CommandArg


assets_dir = os.path.join(os.path.dirname(__file__), "assets")

cooldown_tracker = {}
cooldown_period = 30

def emojiChoice(type_name):
    type_dir = os.path.join(assets_dir, type_name)
    if not os.path.isdir(type_dir):
        return None
    logger.info(f"Searching for GIF files in {type_dir}")
    files = [f for f in os.listdir(type_dir) if f.lower().endswith(".gif")]
    if not files:
        logger.error(f"No GIF files found in {type_dir}")
        return None
    return os.path.join(type_dir, random.choice(files))

huizhua = on_regex(pattern = r"^挥爪$", priority=1)
@huizhua.handle()
async def huizhuar(bot: Bot, event: GroupMessageEvent):
    gif_path = emojiChoice("wave")
    if not gif_path:
        await huizhua.finish("没有找到挥爪表情")
    await huizhua.finish(MessageSegment.image(gif_path))