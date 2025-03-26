from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Message, LuckyKingNotifyEvent # type: ignore
from nonebot import on_notice
import os, json, random

RPluckyKing = on_notice()

@RPluckyKing.handle()
async def RPluckyKing (bot: Bot, event: LuckyKingNotifyEvent, state: T_State):
    user = event.get_user_id()
    at = "[CQ:at,qq={}]".format(user)
    with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Replies.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
        Congrats = data.get('Congrats', [])
    msg = at + " " + random.choice(Congrats)
    await RPluckyKing.finish(message=Message(f'{msg}'))