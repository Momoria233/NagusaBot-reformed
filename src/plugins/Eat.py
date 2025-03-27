from nonebot import on_regex
import random, os, json
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message # type: ignore

EatL = on_regex(pattern=r'^吃饭$',priority=1)

@EatL.handle()
async def Eat (bot: Bot, event: GroupMessageEvent, state: T_State):
    with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Replies.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
        food = data.get('food', [])
        stu = data.get('stu', [])

    randList = food + stu
    msg = f"吃到了{random.choice(randList)}。"
    await EatL.finish(message=Message(msg))
