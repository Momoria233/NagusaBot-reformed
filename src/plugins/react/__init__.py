import os
import random
import time
from datetime import datetime

from nonebot import logger, on_notice, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    LuckyKingNotifyEvent,
    Message,
    MessageSegment,
    PokeNotifyEvent,
)
from nonebot.typing import T_State

from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period


def usr_cd_check(user_id: str) -> bool:
    current_time = time.time()
    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            return False
    cooldown_tracker[user_id] = current_time
    return True


EatL = on_regex(pattern=r"^吃饭$", priority=1)


@EatL.handle()
async def Eat(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await EatL.finish()
    if not Config.activate_eat:
        await EatL.finish()
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}"
    randFood = random.choice(Config.food + Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[70, 30], k=1)[0]
    msg = f" 吃到了{selected_food}。"
    await EatL.finish(message=Message([at, msg]))


Touxiang = on_regex(pattern=r"^投降$", priority=1)


@Touxiang.handle()
async def Touxiang(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    if not usr_cd_check(user_id):
        await Touxiang.finish()
    msg = "🏳"
    await Touxiang.finish(message=Message([msg]))

Start_TotalAst = on_regex(pattern=r"^开票$", priority=1)


@Start_TotalAst.handle()
async def StartTotalAst(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await Start_TotalAst.finish()
    if not Config.activate_TotalAst:
        await Start_TotalAst.finish()
    opt = ["炸票", "出分"]
    selected_difficulty = random.choices(Config.Total_Assault_difficulty, weights=[2, 2, 3, 3, 20, 50, 20], k=1)[0]
    Total_Assault = f" 打了{selected_difficulty}难度的{random.choice(Config.Total_Assault_bosslist)}，{random.choice(opt)}了。"
    await Start_TotalAst.finish(message=Message([at, Total_Assault]))


pokeReact = on_notice()


@pokeReact.handle()
async def pokeReaction(bot: Bot, event: PokeNotifyEvent, state: T_State):
    if not Config.activate_poke:
        await pokeReact.finish()
    if event.target_id == event.self_id:
        at = MessageSegment.at(event.get_user_id())
        msg = MessageSegment.text(" " + random.choice(Config.react))
        await pokeReact.finish(message=Message([at, msg]))


RPluckyKing = on_notice()


@RPluckyKing.handle()
async def RPluckyKingFunc(bot: Bot, event: LuckyKingNotifyEvent, state: T_State):
    if not Config.activate_congrat:
        await RPluckyKing.finish()
    at = MessageSegment.at(event.get_user_id())
    msg = MessageSegment.text(" " + random.choice(Config.Congrats))
    await pokeReact.finish(message=Message([at, msg]))


nao = on_regex(pattern=r"^闹了$", priority=1)


@nao.handle()
async def naoL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await nao.finish()
    if event.group_id in Config.ai_group_whitelist:
        await nao.finish(message=Message([at, MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "naole.png"))]))
    else:
        await nao.finish()


aiyou = on_regex(pattern=r"^哎呦$", priority=1)


@aiyou.handle()
async def aiyouL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await aiyou.finish()
    if event.group_id in Config.ai_group_whitelist:
        logger.info(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buxuaiyou.jpg"))
        await aiyou.finish(message=Message([at, MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buxuaiyou.jpg"))]))
    else:
        await aiyou.finish()


aiai = on_regex(pattern=r"^唉唉$", priority=1)


@aiai.handle()
async def aiaiL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await aiai.finish()
    if event.group_id in Config.ai_group_whitelist:
        if user_id in Config.ai_usr_whitelist:
            await aiai.finish()
        else:
            logger.info(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buzhunaiai.png"))
            await aiai.finish(message=Message([at, MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buzhunaiai.png"))]))
    else:
        await aiai.finish()


zhalan = on_regex(pattern=r"^栅栏$", priority=1)


@zhalan.handle()
async def zhalanL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await zhalan.finish()
    if event.group_id in Config.ai_group_whitelist:
        await zhalan.finish(message=Message([at, MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhalan.jpg"))]))
    else:
        await zhalan.finish()


haqi = on_regex(pattern=r"哈气|哈氣|蛤气|哈気|哈汽|啥气|あくびをする|24|噺气", priority=1)


@haqi.handle()
async def haqiL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await haqi.finish()
    if event.group_id in Config.ai_group_whitelist:
        msg = " 哈气要交税！"
        await haqi.finish(message=Message([at, msg]))
    else:
        await haqi.finish()

pinhaofan = on_regex(pattern=r"^拼好饭$", priority=1)


@pinhaofan.handle()
async def pin(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await pinhaofan.finish()
    if not Config.activate_eat:
        await pinhaofan.finish()
    if random.random() < 0.05:
        msg = f" {at} 你的拼好饭被偷了！"
        await pinhaofan.finish(message=Message([msg]))
    if random.random() < 0.03:
        msg = f" {at} 很遗憾，人数太少拼团失败了"
        await pinhaofan.finish(message=Message([msg]))
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}"
    randFood = random.choice(Config.food + Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[70, 30], k=1)[0]
    msg = f" 您与{random.randint(1,1052)}位群友一起拼到了{selected_food}，为您节省了{round(random.uniform(1,20),2)}元。"
    await pinhaofan.finish(message=Message([at, msg]))
