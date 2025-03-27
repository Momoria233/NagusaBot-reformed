from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message  # type: ignore

nao = on_regex(pattern=r"^闹了$", priority=1)


@nao.handle()
async def naoL(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = f"这里应该是输出一张闹了对应的图片 但我还没写完 就先占个位置（"
    await nao.finish(message=Message(msg))
