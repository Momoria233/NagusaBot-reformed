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
from src.common.feature_manager import feature_manager
from src.common.config import global_config
from src.common.resource import resource_manager

# Register features
feature_manager.register("哈气", ": \n哈气要交税！")
feature_manager.register("我超 盒", ": \n或许是字面意思...?")
feature_manager.register("吃史", ": \n在群内发送 吃史 可以吃到一些奇怪的东西。")
feature_manager.register("吃饭", ": \n随机吃点什么")
feature_manager.register("投降", ": \n发送 投降")
feature_manager.register("开票", ": \n蔚蓝档案总力战模拟")
feature_manager.register("手气王", ": \n红包手气王嘲讽")
feature_manager.register("拼好饭", ": \n模拟拼好饭")
feature_manager.register("戳一戳", ": \n戳一戳机器人的反应")

# Get assets directory (Plugin-bundled assets)
assets_dir = resource_manager.get_bundled_asset_dir(__file__)

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
    if not feature_manager.is_enabled(event.group_id, "哈气"):
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
    if event.group_id and not feature_manager.is_enabled(event.group_id, "戳一戳"):
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

he = on_regex(pattern=r"^我超.*盒$")
@he.handle()
async def he_handle(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "我超 盒"):
        return
    at = MessageSegment.at(event.get_user_id())
    if not usr_cd_check(event.get_user_id()):
        await he.finish()
    try:
        await he.finish(message=Message([at,MessageSegment.record(file=assets_dir / "he.mp3")]))
    except nonebot.exception.FinishedException:
        pass
    except Exception as e:
        logger.error(e)

chishiL = on_regex(pattern=r"^吃史$")
@chishiL.handle()
async def chishi(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "吃史"):
        return
    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await chishiL.finish()
    # Removing Config.activate_eat check, relying on feature_manager (which is checked above? No, wait. 
    # The original code had separate checks. "吃史" feature is checked at top. 
    # But for "吃饭", we need to check "吃饭" feature.
    await chishiL.finish(message=Message([at," 吃到了史"]))


EatL = on_regex(pattern=r"^吃饭$")
@EatL.handle()
async def Eat(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "吃饭"):
        return

    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await EatL.finish()
        
    Total_Assult_food = f"{random.choice(Config.Total_Assault_difficulty)}难度的{random.choice(Config.Total_Assault_bosslist)}"
    randFood = random.choice(Config.food+Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[85, 15], k=1)[0]
    msg = f" 吃到了{selected_food}。"
    await EatL.finish(message=Message([at, msg]))


Touxiang = on_regex(pattern=r"^投降$")
@Touxiang.handle()
async def TouxiangL(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "投降"):
        return

    user_id = event.get_user_id()
    if not usr_cd_check(user_id):
        await Touxiang.finish()
    msg = "🏳"
    await Touxiang.finish(message=Message([msg]))

Start_TotalAst = on_regex(pattern=r"^开票$")
@Start_TotalAst.handle()
async def StartTotalAst(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "开票"):
        return

    user_id = event.get_user_id()
    at = MessageSegment.at(user_id)
    if not usr_cd_check(user_id):
        await Start_TotalAst.finish()
        
    opt = ["炸票", "出分"]
    selected_difficulty = random.choices(Config.Total_Assault_difficulty, weights=[2, 2, 3, 3, 20, 50, 20], k=1)[0]
    Total_Assault = f" 打了{selected_difficulty}难度的{random.choice(Config.Total_Assault_bosslist)}，{random.choice(opt)}了。"
    await Start_TotalAst.finish(message=Message([at, Total_Assault]))

RPluckyKing = on_notice()
@RPluckyKing.handle()
async def RPluckyKingFunc(bot: Bot, event: LuckyKingNotifyEvent):
    if not feature_manager.is_enabled(event.group_id, "手气王"):
        return

    at = MessageSegment.at(event.get_user_id())
    msg = MessageSegment.text(" " + random.choice(Config.Congrats))
    await RPluckyKing.finish(message=Message([at, msg]))

pinhaofan = on_regex(pattern=r"^拼好饭$")
@pinhaofan.handle()
async def pin(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "拼好饭"):
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
    randFood = random.choice(Config.food+Config.stu)
    selected_food = random.choices([randFood, Total_Assult_food], weights=[85, 15], k=1)[0]
    msg = f" 您与{random.randint(1,1052)}位群友一起拼到了{selected_food}，为您节省了{round(random.uniform(1,20),2)}元。"
    await pinhaofan.finish(message=Message([at, msg]))
