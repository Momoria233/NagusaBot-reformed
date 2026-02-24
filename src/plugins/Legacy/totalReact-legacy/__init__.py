import os
import random
import time
import nonebot
from nonebot import on_command, on_regex, logger, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    Message,
    GroupMessageEvent,
    LuckyKingNotifyEvent,
    MessageSegment,
    PokeNotifyEvent
)
from .config import Config
from nonebot.typing import T_State
from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.config import global_config
from src.common.plugin_config import get_assets_dir

PLUGIN_REG_NAME = "totalReact-legacy"
PLUGIN_REAL_NAME = ""
FEATURE_WAVE = "挥爪"
# FEATURE_HE = "我超 盒"
FEATURE_PINHAOFAN = "吃饭/拼好饭"
FEATURE_POKE = "戳一戳"
FEATURE_KAIPIAO = "开票"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[
        FeatureSpec(name=FEATURE_WAVE, default_open=True, description="发送“挥爪”可以得到可爱学生挥爪表情包！"),
        # FeatureSpec(name=FEATURE_HE, default_open=True, description="或许是字面意思...?"),
        FeatureSpec(name=FEATURE_PINHAOFAN, default_open=True, description="在群里直接发送吃饭/拼好饭可以吃到/拼到一些奇怪的东西"),
        FeatureSpec(name=FEATURE_POKE, default_open=True, description="戳一戳bot或许会得到一些意想不到的东西！"),
        FeatureSpec(name=FEATURE_KAIPIAO, default_open=True, description="在群内发送 开票 可以模拟总力战，但是请小心炸票哦"),
    ],
    group_customize=True,
)

assets_dir = get_assets_dir(__file__)

cooldown_tracker = {}

def usr_cd_check(user_id: str) -> bool:
    current_time = time.time()
    # Use global config for whitelist
    if user_id in global_config.total_react_whitelist:
        return True
    
    if user_id in cooldown_tracker:
        last_used = cooldown_tracker[user_id]
        # Use global config for cooldown period
        if current_time - last_used < global_config.total_react_cooldown:
            return False
            
    cooldown_tracker[user_id] = current_time
    return True

def emojiChoice(type_name):
    type_dir = assets_dir / type_name
    if not type_dir.is_dir():
        return None
    
    # logger.info(f"Searching for GIF files in {type_dir}")
    files = [f.name for f in type_dir.iterdir() if f.suffix.lower() in [".gif", ".jpg", ".png"]]
    
    if not files:
        logger.error(f"No image files found in {type_dir}")
        return None
    return type_dir / random.choice(files)

huizhua = on_regex(pattern = r"^挥爪$")
@huizhua.handle()
async def huizhuar(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_WAVE, event.group_id, event.user_id):
        return
    gif_path = emojiChoice("wave")
    if not gif_path:
        await huizhua.finish("没有找到挥爪表情")
    await huizhua.finish(MessageSegment.image(gif_path))
    

pokeReact = on_notice()
@pokeReact.handle()
async def pokeReaction(bot: Bot, event: PokeNotifyEvent):
    if event.target_id != event.self_id:
        await pokeReact.finish()
    
    # Check if enabled for this group (if it's a group event)
    if event.group_id and not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_POKE, event.group_id, event.user_id
    ):
         await pokeReact.finish()

    ret = random.randint(0,2)
    if ret == 0:
        jpg_path = emojiChoice("cute")
        if not jpg_path:
            await pokeReact.finish("没有找到戳一戳表情")
        await pokeReact.finish(MessageSegment.image(jpg_path))
    elif ret == 1:
        gif_path = emojiChoice("wave")
        if not gif_path:
            await pokeReact.finish("没有找到挥爪表情")
        await pokeReact.finish(MessageSegment.image(gif_path))
    else:
        at = MessageSegment.at(event.get_user_id())
        msg = MessageSegment.text(" " + random.choice(Config.react))
        await pokeReact.finish(message=Message([at, msg]))


# 下为旧React部分

# he = on_regex(pattern=r"^我超.*盒$")
# @he.handle()
# async def he_handle(bot: Bot, event: GroupMessageEvent):
#     if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_HE, event.group_id, event.user_id):
#         return
#     at = MessageSegment.at(event.get_user_id())
#     if not usr_cd_check(event.get_user_id()):
#         await he.finish()
#     try:
#         await he.finish(message=Message([at,MessageSegment.record(file=assets_dir / "he.mp3")]))
#     except nonebot.exception.FinishedException:
#         pass
#     except Exception as e:
#         logger.error(e)

chishiL = on_regex(pattern=r"^吃史$")
@chishiL.handle()
async def chishi(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_PINHAOFAN, event.group_id, event.user_id):
        return
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await chishiL.finish()
    await chishiL.finish(message=Message([at," 吃到了史"]))


EatL = on_regex(pattern=r"^吃饭$")
@EatL.handle()
async def Eat(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_PINHAOFAN, event.group_id, event.user_id):
        return

    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await EatL.finish()
        
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}"
    # randFood = random.choice(Config.food+Config.stu)
    randFood = random.choice(Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[85, 15], k=1)[0]
    msg = f" 吃到了{selected_food}。"
    await EatL.finish(message=Message([at, msg]))


Touxiang = on_regex(pattern=r"^投降$")
@Touxiang.handle()
async def TouxiangL(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_WAVE, event.group_id, event.user_id):
        return

    user_id = event.get_user_id()
    if not usr_cd_check(user_id):
        await Touxiang.finish()
    msg = "🏳"
    await Touxiang.finish(message=Message([msg]))

Start_TotalAst = on_regex(pattern=r"^开票$")
@Start_TotalAst.handle()
async def StartTotalAst(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_KAIPIAO, event.group_id, event.user_id):
        return

    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await Start_TotalAst.finish()
        
    opt = ["炸票", "出分"]
    selected_difficulty = random.choices(Config.Total_Assault_difficulty, weights=[2, 2, 3, 3, 20, 50, 20], k=1)[0]
    Total_Assault = f" 打了{selected_difficulty}难度的{random.choice(Config.Total_Assault_bosslist)}，{random.choice(opt)}了。"
    await Start_TotalAst.finish(message=Message([at, Total_Assault]))

pinhaofan = on_regex(pattern=r"^拼好饭$")
@pinhaofan.handle()
async def pin(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_PINHAOFAN, event.group_id, event.user_id):
        return

    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await pinhaofan.finish()
        
    if random.random() < 0.05:
        msg = f" {at} 你的拼好饭被偷了！"
        await pinhaofan.finish(message=Message([msg]))
    if random.random() < 0.03:
        msg = f" {at} 很遗憾，人数太少拼团失败了"
        await pinhaofan.finish(message=Message([msg]))
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}"
    # randFood = random.choice(Config.food+Config.stu)
    randFood = random.choice(Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[85, 15], k=1)[0]
    msg = f" 您与{random.randint(1,1052)}位群友一起拼到了{selected_food}，为您节省了{round(random.uniform(1,20),2)}元。"
    await pinhaofan.finish(message=Message([at, msg]))

baijian  = on_regex(pattern=r"速速拜见$")
@baijian.handle()
async def baijianL(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if user_id == "1051575616":
        await baijian.finish(message=Message([at," 拜见岁大王！"]))
    else:
        await baijian.finish()

jd  = on_regex(pattern=r"雪诺驾到$")
@jd.handle()
async def jdL(bot: Bot, event: GroupMessageEvent, state: T_State):
    if event.group_id != 1077304925:
        return
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if user_id == "3291407469":
        await jd.finish(message=Message([at," 雪诺大小姐好！"]))
    else:
        await jd.finish()

liuerling  = on_regex(pattern=r"^620$")
@liuerling.handle()
async def liuerlingL(bot: Bot, event: GroupMessageEvent, state: T_State):
    if event.group_id != 996101999:
        return
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    await liuerling.finish(message=Message([at," 所以620是什么意思？？难道是指一个叫特儿的扫群友于2026年1月23日在宜必思酒店 (天津火车站津湾广场店)六楼找不到620在哪，于是在北京bao群问620在哪吗？"]))
