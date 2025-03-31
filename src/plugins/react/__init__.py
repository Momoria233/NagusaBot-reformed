import random, os, time
from nonebot import on_notice, on_regex
from nonebot.typing import T_State
from nonebot import logger
from nonebot.adapters.onebot.v11 import PokeNotifyEvent, LuckyKingNotifyEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from .config import Config

cooldown_tracker = {}
cooldown_period = Config.cooldown_period

EatL = on_regex(pattern=r"^吃饭$", priority=1)

@EatL.handle()
async def Eat(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    current_time = time.time()
    at = MessageSegment.at(event.get_user_id())

    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            remaining_time = cooldown_period - (current_time - last_used)
            await EatL.finish()
    cooldown_tracker[user_id] = current_time

    if not Config.activate_eat:
        await EatL.finish()
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}。"
    randFood =random.choice(Config.food + Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[70, 30], k=1)[0]
    msg = f" 吃到了{selected_food}。"
    await EatL.finish(message=Message([at,msg]))

Start_TotalAst = on_regex(pattern=r"开票", priority=1)

@Start_TotalAst.handle()
async def StartTotalAst(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    current_time = time.time()
    at = MessageSegment.at(event.get_user_id())

    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            remaining_time = cooldown_period - (current_time - last_used)
            await Start_TotalAst.finish()
    cooldown_tracker[user_id] = current_time

    if not Config.activate_TotalAst:
        await Start_TotalAst.finish()
    opt = ["炸票","出分"]
    selected_difficulty = random.choices(Config.Total_Assault_difficulty, weights=[2, 2, 3, 3, 20, 50, 20], k=1)[0]
    Total_Assault = f" 打了{selected_difficulty}难度的{random.choice(Config.Total_Assault_bosslist)}，{random.choice(opt)}了。"
    await Start_TotalAst.finish(message=Message([at,Total_Assault]))


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
    current_time = time.time()
    at = MessageSegment.at(event.get_user_id())

    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            remaining_time = cooldown_period - (current_time - last_used)
            await nao.finish()
    cooldown_tracker[user_id] = current_time

    if event.group_id == 996101999 or event.group_id == 225173408:
        await nao.finish(message = Message([at,MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "naole.png"))]))
    else:
        await nao.finish()


aiyou = on_regex(pattern=r"^哎呦$", priority=1)

@aiyou.handle()
async def aiyouL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    current_time = time.time()
    at = MessageSegment.at(event.get_user_id())

    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            remaining_time = cooldown_period - (current_time - last_used)
            await aiyou.finish()
    cooldown_tracker[user_id] = current_time

    if event.group_id == 996101999 or event.group_id == 225173408:
        logger.info(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buxuaiyou.jpg"))
        await aiyou.finish(message = Message([at,MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buxuaiyou.jpg"))]))
    else:
        await aiyou.finish()


aiai = on_regex(pattern=r"^唉唉$", priority=1)

@aiai.handle()
async def aiaiL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    current_time = time.time()
    at = MessageSegment.at(event.get_user_id())

    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        if current_time - last_used < cooldown_period:
            remaining_time = cooldown_period - (current_time - last_used)
            await aiai.finish()
    cooldown_tracker[user_id] = current_time

    if event.group_id == 996101999 or event.group_id == 225173408:
        if event.get_user_id() == "2891544717":
            await aiai.finish()
        else:
            logger.info(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buzhunaiai.png"))
            await aiai.finish(message = Message([at,MessageSegment.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), "buzhunaiai.png"))]))
    else:
        await aiai.finish()