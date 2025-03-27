from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message  # type: ignore
import re

bao = on_regex(pattern=r"^bao$", flags=re.IGNORECASE, priority=1)


@bao.handle()
async def baoT(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = f"bao输出测试。"
    await bao.finish(message=Message(msg))
