from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Message, PokeNotifyEvent # type: ignore
from nonebot import on_notice
import os, json, random

pokeReact = on_notice()

@pokeReact.handle()
async def pokeReaction (bot: Bot, event: PokeNotifyEvent, state: T_State):
    if event.target_id == event.self_id:
        user = event.get_user_id()
        at = "[CQ:at,qq={}]".format(user)
        # print(at)
        # msg = at + "唔" #其实这里可以再单开一个json创建不同的回复比如蹭蹭之类的 但是没想好要写啥回复
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Replies.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            reaction = data.get('react', [])

        msg = at + " " + random.choice(reaction)
        await pokeReact.finish(message=Message(f'{msg}'))
